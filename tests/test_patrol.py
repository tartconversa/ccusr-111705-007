import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.site import DATA
from app.patrol import inspect_access
from app.records import save_access_reviews, read_access_reviews
from app.review import summarize_access_reviews
from test_browser import BrowserBaselineTest


class AccessPatrolTest(BrowserBaselineTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.result = inspect_access(cls.origin)
        cls.records = cls.result['records']

    def _records_of(self, item_id):
        return [r for r in self.records if r['item_id'] == item_id]

    def test_every_service_floor_pair_is_recorded_without_merging(self):
        expected_pairs = {
            (item['id'], row['floor'])
            for item in DATA['items']
            for row in item['floors']
        }
        observed_pairs = {(r['item_id'], r['floor']) for r in self.records}
        self.assertEqual(expected_pairs, observed_pairs)
        # 业务键包含楼层与服务日，同名服务不同楼层不得合并。
        keys = [r['business_key'] for r in self.records]
        self.assertEqual(len(keys), len(set(keys)))
        senior01 = self._records_of('senior-01')
        self.assertEqual({r['floor'] for r in senior01}, {'一层', '二层'})
        self.assertNotEqual(senior01[0]['business_key'], senior01[1]['business_key'])

    def test_floor_filter_changes_observed_service_day(self):
        senior01 = {r['floor']: r for r in self._records_of('senior-01')}
        self.assertEqual(senior01['一层']['floor_filter']['service_day'], '周二开放')
        self.assertEqual(senior01['二层']['floor_filter']['service_day'], '周四开放')
        self.assertFalse(senior01['一层']['floor_filter']['pending_slot'])

    def test_pending_slot_is_reported_as_unknown_not_unreachable(self):
        third = next(r for r in self._records_of('senior-02') if r['floor'] == '三层')
        self.assertTrue(third['floor_filter']['pending_slot'])
        self.assertIn('unknown_slot', third['verdict']['unknown'])
        self.assertEqual(third['verdict']['preview_state'], 'unavailable')
        self.assertIn('时段待公布', third['preview']['after_mouse_terms']['text'])
        self.assertEqual(third['verdict']['reachability'], 'partially_reachable')
        # 键盘阻断步骤不被“未知”结论掩盖，仍然如实保留。
        self.assertIsNotNone(third['verdict']['keyboard_blocked_step'])

    def test_keyboard_path_records_focus_and_terms_separately_from_mouse(self):
        defective = next(r for r in self._records_of('senior-02') if r['floor'] == '二层')
        self.assertTrue(defective['mouse']['opened'])
        self.assertTrue(defective['keyboard']['opened'])
        # 键盘打开弹窗但焦点停在触发按钮，阻断步骤被明确指出。
        self.assertFalse(defective['keyboard']['focus_inside'])
        self.assertEqual(defective['keyboard']['blocked_step'], 'dialog_focus_blocked')
        self.assertEqual(defective['verdict']['keyboard_blocked_step'], 'dialog_focus_blocked')
        # 键盘与鼠标读到的服务说明文本不同，且不被静态卡片文字掩盖。
        self.assertNotEqual(defective['mouse']['terms_text'], defective['keyboard']['terms_text'])
        self.assertIn('keyboard_terms_mismatch', defective['verdict']['unknown'])
        self.assertNotIn(defective['keyboard']['terms_text'], defective['catalog_summary'])

    def test_healthy_service_is_keyboard_reachable_end_to_end(self):
        healthy = next(r for r in self._records_of('senior-01') if r['floor'] == '一层')
        self.assertTrue(healthy['mouse']['opened'])
        self.assertTrue(healthy['keyboard']['opened'])
        self.assertTrue(healthy['keyboard']['focus_inside'])
        self.assertTrue(healthy['keyboard']['dismissed'])
        self.assertEqual(healthy['mouse']['terms_text'], healthy['keyboard']['terms_text'])
        self.assertEqual(healthy['verdict']['reachability'], 'reachable')
        self.assertIsNone(healthy['verdict']['keyboard_blocked_step'])

    def test_async_panel_and_preview_come_from_live_regions_not_static_cards(self):
        record = self._records_of('senior-01')[0]
        for path in ('mouse', 'keyboard'):
            panel = record['async_panel'][path]
            self.assertTrue(panel['settled'])
            self.assertNotIn('读取中', panel['text'])
            self.assertIn(record['name'], panel['text'])
        # 预约预览先提示“说明待核对”，鼠标核对后才显示已打开。
        self.assertIn('说明待核对', record['preview']['before_opening_terms']['text'])
        self.assertIn('服务说明已打开', record['preview']['after_mouse_terms']['text'])
        self.assertEqual(record['preview']['state'], 'confirmed_preview')
        # 静态卡片只有目录摘要，异步文本来自详情页实时区域。
        self.assertNotEqual(record['preview']['after_mouse_terms']['text'], record['catalog_summary'])

    def test_floor_switch_resets_preview_and_dialog(self):
        first = next(r for r in self._records_of('senior-01') if r['floor'] == '一层')
        second = next(r for r in self._records_of('senior-01') if r['floor'] == '二层')
        # 切到新楼层后的第一次预览必须重新要求核对，而不是沿用上一楼层状态。
        self.assertIn('说明待核对', second['preview']['before_opening_terms']['text'])
        self.assertIn('周四开放', second['preview']['after_mouse_terms']['text'])
        self.assertNotEqual(first['business_key'], second['business_key'])

    def test_flow_is_read_only_no_submission_and_no_personal_data(self):
        for request in self.result['requests']:
            self.assertEqual(request['method'], 'GET')
        for record in self.records:
            self.assertFalse(record['verdict']['booking_submitted'])
            serialized = str(record)
            for forbidden in ('身份证', '手机号', '姓名填写', 'type="submit"'):
                self.assertNotIn(forbidden, serialized)

    def test_non_loopback_origin_is_rejected(self):
        with self.assertRaises(ValueError):
            inspect_access('https://example.com/')

    def test_access_reviews_are_append_only_per_floor_and_summarized(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'access.sqlite3'
            self.assertEqual(save_access_reviews(database, self.records), len(self.records))
            save_access_reviews(database, self.records[:1])
            with sqlite3.connect(database) as db:
                total = db.execute('SELECT count(*) FROM access_reviews').fetchone()[0]
                distinct = db.execute('SELECT count(DISTINCT business_key) FROM access_reviews').fetchone()[0]
            self.assertEqual(total, len(self.records) + 1)
            self.assertEqual(distinct, len(self.records))
            loaded = read_access_reviews(database)
            summary = summarize_access_reviews(loaded)
            by_key = {row['business_key']: row for row in summary}
            defective_key = next(
                r['business_key'] for r in self.records
                if r['item_id'] == 'senior-02' and r['floor'] == '二层'
            )
            self.assertEqual(by_key[defective_key]['reachability'], 'keyboard_blocked')
            self.assertIsNotNone(by_key[defective_key]['keyboard_blocked_note'])
            self.assertFalse(any(row['booking_submitted'] for row in summary))

    def test_unknown_item_id_is_rejected(self):
        with self.assertRaises(ValueError):
            inspect_access(self.origin, item_ids=['missing-service'])

    def test_read_only_guard_blocks_submit_controls_and_forms(self):
        from app.patrol import _ReadOnlyGuard
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                guard = _ReadOnlyGuard(page.context)
                page.set_content(
                    '<button id="ok" type="button">说明</button>'
                    '<form method="post" action="/book">'
                    '<button id="send" type="submit">提交预约</button>'
                    '<input id="name" name="name">'
                    '<a id="external" href="https://example.com/">外站</a>'
                    '</form>'
                )
                # 普通说明按钮放行。
                guard.safe_click(page, '#ok')
                with self.assertRaises(PermissionError):
                    guard.safe_click(page, '#send')
                with self.assertRaises(PermissionError):
                    guard.safe_click(page, '#name')
                with self.assertRaises(PermissionError):
                    guard.safe_click(page, '#external')
            finally:
                browser.close()


if __name__ == '__main__':
    unittest.main()
