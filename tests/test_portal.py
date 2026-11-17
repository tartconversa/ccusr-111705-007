import unittest
from playwright.sync_api import sync_playwright
from test_browser import BrowserBaselineTest
from app.site import DATA

class PortalInteractionTest(BrowserBaselineTest):
    def test_browser_business_interaction(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(self.origin + "detail?id=" + DATA["items"][0]["id"], wait_until="domcontentloaded")
                page.locator('#access').focus();page.keyboard.press('Enter');self.assertTrue(page.locator('#access-dialog').is_visible());page.locator('#floor').select_option('二层');self.assertFalse(page.locator('#access-dialog').is_visible());self.assertEqual(page.locator('#service-day').inner_text(),'周四开放')
            finally:
                browser.close()
