from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Login
    page.goto("http://localhost:8000/login/")
    page.fill('input[name="username"]', 'testuser')
    page.fill('input[name="password"]', 'testpassword')
    page.click('button[type="submit"]')
    page.wait_for_url("http://localhost:8000/search/")

    # Search for a new keyword
    page.fill('input[name="keyword"]', 'Apple')
    page.click('button[type="submit"]')

    # Should be on the loading page
    page.wait_for_url("**/loading/**")

    # Wait for the result link to appear, which means the task is complete
    result_link = page.locator("#result-link a")
    expect(result_link).to_be_visible(timeout=120000) # 2 minutes timeout

    # Click the link to go to the results page
    result_link.click()

    # Verify that we are on the results page and the content is correct
    page.wait_for_url("**/search/**")
    expect(page.locator("text=Apple")).to_be_visible()

    page.screenshot(path="jules-scratch/on_demand_results.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
