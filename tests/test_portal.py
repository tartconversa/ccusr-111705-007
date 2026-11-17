import unittest
from playwright.sync_api import sync_playwright
from test_browser import BrowserBaselineTest
from app.site import DATA
from app.capture import read_detail_entry
from app.records import save_detail_entries, read_detail_entries
from app.review import review_entries
from tempfile import TemporaryDirectory
from pathlib import Path
import sqlite3

class PortalInteractionTest(BrowserBaselineTest):
    def test_floor_focus_and_preview_propagate(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(self.origin + 'detail?id=' + DATA['items'][0]['id'])
                page.locator('#access').focus()
                page.keyboard.press('Enter')
                self.assertTrue(page.locator('#access-dialog').is_visible())
                page.locator('#preview').click()
                self.assertIn('服务说明已打开', page.locator('#assistance-preview').inner_text())
                page.locator('#floor').select_option('二层')
                self.assertFalse(page.locator('#access-dialog').is_visible())
                page.locator('#preview').click()
                self.assertIn('说明待核对', page.locator('#assistance-preview').inner_text())
            finally:
                browser.close()
    def test_selected_business_state_reaches_receipt(self):
        initial = read_detail_entry(self.origin, DATA['items'][0]['id'])
        changed = read_detail_entry(self.origin, DATA['items'][0]['id'], '二层')
        self.assertNotEqual(initial['detail_fact']['business_key'], changed['detail_fact']['business_key'])
        with TemporaryDirectory() as directory:
            database = Path(directory) / 'selected.sqlite3'
            save_detail_entries(database, [initial, changed])
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute('SELECT count(DISTINCT business_key) FROM detail_entries').fetchone()[0], 2)
            review = review_entries(read_detail_entries(database))
            self.assertEqual(len(review), 2)
            self.assertIn('unconfirmed' if 'unconfirmed' in str(review) else 'not_observed', str(review))
    def test_distinct_source_state_transitions(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(self.origin + 'detail?id=' + DATA['items'][0]['id'], wait_until='domcontentloaded')
                page.locator('#floor').select_option('二层')
                page.locator('#preview').click()
                self.assertIn('说明待核对', page.locator('#assistance-preview').inner_text())
                page.locator('#access').focus()
                page.keyboard.press('Enter')
                page.locator('#preview').click()
                self.assertIn('周四开放', page.locator('#assistance-preview').inner_text())
            finally:
                browser.close()
    def test_entry_visit_is_append_only_and_linked(self):
        entry = read_detail_entry(self.origin, DATA['items'][0]['id'])
        self.assertEqual(entry['catalog_fact']['identity'], entry['id'])
        self.assertIn('detail', entry['source'])
        self.assertIn(DATA['items'][0]['id'], entry['detail_fact']['business_key'])
        with TemporaryDirectory() as directory:
            database = Path(directory) / 'visits.sqlite3'
            save_detail_entries(database, [entry, entry])
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM detail_entries').fetchone()[0], 2)
                self.assertEqual(db.execute('SELECT count(DISTINCT business_key) FROM detail_entries').fetchone()[0], 1)

    def test_browser_business_interaction(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(self.origin + "detail?id=" + DATA["items"][0]["id"], wait_until="domcontentloaded")
                page.locator('#access').focus();page.keyboard.press('Enter');self.assertTrue(page.locator('#access-dialog').is_visible());page.locator('#floor').select_option('二层');self.assertFalse(page.locator('#access-dialog').is_visible());self.assertEqual(page.locator('#service-day').inner_text(),'周四开放')
            finally:
                browser.close()
