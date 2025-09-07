from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Start the server in the background
    # I will assume the server is running on port 8000

    # Login
    page.goto("http://localhost:8000/login/")
    page.fill('input[name="username"]', 'testuser')
    page.fill('input[name="password"]', 'testpassword')
    page.click('button[type="submit"]')
    page.wait_for_url("http://localhost:8000/search/")

    # Search
    page.fill('input[name="keyword"]', 'TCS')
    page.click('button[type="submit"]')

    # Verify results
    page.wait_for_selector("text=TCS among top 10 high-yield dividend stocks")

    # Take a screenshot
    page.screenshot(path="jules-scratch/search_results.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
