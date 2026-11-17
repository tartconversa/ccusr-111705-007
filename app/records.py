"""公开目录收据，不把目录缺失解释为详情不存在。"""
import json
import sqlite3
from pathlib import Path

def save_catalog(path, items):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS catalog (id TEXT PRIMARY KEY, source TEXT NOT NULL, payload TEXT NOT NULL)')
        for item in items:
            db.execute('INSERT OR REPLACE INTO catalog VALUES (?, ?, ?)', (item['id'], item['source'], json.dumps(item, ensure_ascii=False)))
    return len(items)

def save_detail_entries(path, entries):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS detail_entries (visit_id INTEGER PRIMARY KEY, item_id TEXT NOT NULL, business_key TEXT NOT NULL, source TEXT NOT NULL, payload TEXT NOT NULL)')
        for entry in entries:
            if entry['catalog_fact']['identity'] != entry['id']:
                raise ValueError('catalog and detail identity mismatch')
            db.execute('INSERT INTO detail_entries (item_id, business_key, source, payload) VALUES (?, ?, ?, ?)',
                       (entry['id'], entry['detail_fact']['business_key'], entry['source'], json.dumps(entry, ensure_ascii=False)))
    return len(entries)

def read_detail_entries(path):
    with sqlite3.connect(path) as db:
        rows = db.execute('SELECT payload FROM detail_entries ORDER BY visit_id').fetchall()
    return [json.loads(row[0]) for row in rows]


def save_access_reviews(path, reviews):
    """巡查收据：以“服务 × 楼层”业务键追加，不合并同名服务的不同楼层。

    只保存观察与判定，不把预览核对等同于预约提交。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS access_reviews ('
                   'review_id INTEGER PRIMARY KEY, business_key TEXT NOT NULL,'
                   ' item_id TEXT NOT NULL, floor TEXT NOT NULL,'
                   ' source TEXT NOT NULL, payload TEXT NOT NULL)')
        for review in reviews:
            if review['catalog_fact']['identity'] != review['item_id']:
                raise ValueError('catalog and review identity mismatch')
            if review['verdict'].get('booking_submitted'):
                raise ValueError('巡查记录不得包含已提交预约')
            db.execute('INSERT INTO access_reviews (business_key, item_id, floor, source, payload)'
                       ' VALUES (?, ?, ?, ?, ?)',
                       (review['business_key'], review['item_id'], review['floor'],
                        review['source'], json.dumps(review, ensure_ascii=False)))
    return len(reviews)


def read_access_reviews(path):
    with sqlite3.connect(path) as db:
        rows = db.execute('SELECT payload FROM access_reviews ORDER BY review_id').fetchall()
    return [json.loads(row[0]) for row in rows]
