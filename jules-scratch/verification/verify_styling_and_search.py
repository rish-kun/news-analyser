from playwright.sync_api import sync_playwright, expect
import re

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Login
    page.goto("http://127.0.0.1:8000/login/")
    page.get_by_label("Username").fill("testuser_playwright")
    page.get_by_label("Password").fill("testpassword123")
    page.get_by_role("button", name="Login").click()
    expect(page).to_have_url("http://127.0.0.1:8000/")

    # Navigate to Add Stocks page and take screenshot
    page.goto("http://127.0.0.1:8000/add_stocks/")
    page.screenshot(path="jules-scratch/verification/add_stocks_styled.png")

    # Search for a stock
    page.get_by_placeholder("Search for stocks...").fill("TATA")
    visible_items = page.locator(".stock-item:visible").count()
    assert visible_items > 0
    page.screenshot(path="jules-scratch/verification/add_stocks_filtered.png")

    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
