from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import requests
import time
from playwright.sync_api import sync_playwright
import asyncio
import httpx
import hashlib
import re
from urllib.parse import urlparse, urljoin
import Extract_data_from_url
import Extract_data_from_list
import Extract_data_from_multi_links

###  Main  ###

def scrape_with_fallback(url, class_name=None):
    data = None
    data = selenium_scrape(url)
    if data:
        return data

    data = requests_beautifulsoup_scrape(url)
    if data:
        return data

    data = playwright_scrape(url)
    if data:
        return data

    data = asyncio.run(httpx_async_scrape(url))
    return data


def selenium_scrape(url, class_name=None):
    email = "davidmoreno@72dragons.com"
    password = "DrDragon72!"
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    try:
        driver = webdriver.Chrome(executable_path="/Users/gongyueru/Downloads/chromedriver-mac-arm64 2/chromedriver", options=options)

        driver.get(url)

        if is_login_page(driver):
            print("Detected login page. Attempting to log in...")

            login(driver, email, password)

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        print(f"Accessing URL: {url}")
        driver.get(url)

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        data = extract_data(driver, url, class_name)

        driver.quit()
        return data
    except WebDriverException as e:
        print(f"Failed with Selenium: {e}")
        return None


def is_login_page(driver):
    try:
        # 检测用户名或email字段
        email_field = driver.find_element(By.ID, "Email")
        password_field = driver.find_element(By.ID, "Password")
        return email_field is not None and password_field is not None
    except Exception as e:
        return False


def login(driver, email, password):
    try:
        # enter email and password
        email_field = driver.find_element(By.ID, "Email")
        password_field = driver.find_element(By.ID, "Password")
        submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')

        email_field.send_keys(email)
        password_field.send_keys(password)

        submit_button.click()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    except Exception as e:
        print(f"Error during login: {e}")


def requests_beautifulsoup_scrape(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Make sure to pass the correct fetch_page_content function
        all_data = scrape_with_pagination_generic(soup, fetch_next_page_requests, fetch_next_page_requests)
        return all_data
    except Exception as e:
        print(f"Failed with Requests + BeautifulSoup: {e}")
        return None


def playwright_scrape(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)

            soup = BeautifulSoup(page.content(), 'html.parser')

            # Make sure to pass the correct fetch_page_content function
            all_data = scrape_with_pagination_generic(soup, lambda _: fetch_next_page_playwright(page),
                                                      fetch_next_page_playwright)

            browser.close()
            return all_data
    except Exception as e:
        print(f"Failed with Playwright: {e}")
        return None


async def httpx_async_scrape(url):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            async def fetch_next_page_wrapper(soup):
                next_button = soup.find('a', {'aria-label': 'Next page'})
                if not next_button:
                    print("No 'Next page' button found.")
                    return None
                return await fetch_next_page_httpx(client, next_button['href'])

            # Pass both the get_next_page_url and fetch_page_content functions
            all_data = await scrape_with_pagination_generic(soup, fetch_next_page_wrapper, fetch_next_page_httpx)
            return all_data
    except Exception as e:
        print(f"Failed with httpx + Asyncio + BeautifulSoup: {e}")
        return None



### Paging processing ###

def scrape_with_pagination(driver, url, class_name, base_url):
    # Handling pagination to scrape multiple pages
    all_data = []
    visited_content_hashes = set()
    pages_scraped = 0

    while pages_scraped < 1:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        current_page_hash = hashlib.md5(soup.get_text().encode('utf-8')).hexdigest()

        if current_page_hash in visited_content_hashes:
            print("Already visited this page content. Exiting to prevent a loop.")
            break

        visited_content_hashes.add(current_page_hash)

        # Extract data from the current page
        page_data = Extract_data_from_multi_links.extract_data_with_details(driver, soup, base_url)
        if page_data:
            all_data.extend(page_data)

        if not find_and_click_next_button(driver):
            print("No further 'Next Page' buttons found.")
            break

        time.sleep(2)
        pages_scraped += 1

    return all_data



def scrape_with_pagination_generic(soup, get_next_page_url, fetch_page_content, max_pages=1):
    all_data = []
    initial_content = soup.get_text()
    pages_scraped = 0
    visited_urls = set()

    while pages_scraped < max_pages:
        print("Calling extract_data...")
        page_data = extract_data(soup, url)
        print("Finished calling extract_data.")
        if page_data:
            all_data.extend(page_data)

        next_page_url = get_next_page_url(soup)
        if not next_page_url:
            print("No 'Next page' URL found or all pages scraped.")
            break

        if next_page_url in visited_urls:
            print(f"URL {next_page_url} has already been visited. Exiting to prevent loop.")
            break

        visited_urls.add(next_page_url)

        # Fetch the next page
        soup = fetch_page_content(next_page_url)
        if not soup:
            print("Failed to fetch the next page.")
            break

        if soup.get_text() == initial_content:
            print("Page did not change after clicking 'Next page'. Exiting.")
            break

        initial_content = soup.get_text()
        pages_scraped += 1

    return all_data if all_data else None



def find_and_click_next_button(driver, max_attempts=12):
    try:
        # Define both XPath and CSS selectors for common "Next" button patterns
        next_button_selectors = [
            "//a[contains(@class, 'next')]",
            "//button[contains(@class, 'next')]",
            "//button[@aria-label='Goto next page']",
            "//button[@data-testid='next-page-button']",
            "//button[contains(@class, 'icon-btn')]",
            "//a[contains(text(), 'Next')]",
            "//a[contains(text(), 'next')]",
            "//a[contains(@aria-label, 'Next')]",
            "//button[contains(text(), 'Next')]",
            "//button[contains(text(), 'next')]",
            "//button[contains(@aria-label, 'Next')]",
            "//a[contains(@title, 'Next')]",
            "//a[contains(@role, 'button') and contains(text(), 'Next')]",
            "//a[@rel='next']",
            "//a[contains(@href, 'page') and contains(@href, 'next')]",
            "a[rel='next']",
            "a.pagination__next",
            "a.icon-link",
            "button[aria-label='Goto next page']",
            "a[aria-label='Next page']",
            "//a[@data-test='next-page']",
            "//a[contains(@class, 'pagination') and contains(@class, 'next')]",
            "//li[@class='pagination-next']/a",
            "//a[contains(@class, 'arrow')]",
            "//button[contains(@class, 'arrow')]",
            "//li[contains(@class, 'next')]/a",
            "//a[contains(@class, 'page-next')]",
            "//button[contains(@id, 'next')]",
            "//a[contains(@id, 'next')]",
            "//a[@title='Next']",
            "//div[contains(@class, 'next')]/a",
            "//div[contains(@class, 'pagination')]/a[contains(@class, 'next')]",
        ]

        attempts = 0
        for selector in next_button_selectors:
            if attempts >= max_attempts:
                print("Reached maximum attempts to find the next button.")
                break
            try:
                print(f"Trying selector: {selector}")
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, selector)) if selector.startswith("//")
                    else EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )

                if next_button and next_button.is_enabled() and next_button.is_displayed():
                    # Scroll the element into view before clicking
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)  # Allow time for scrolling
                    driver.execute_script("arguments[0].click();", next_button)
                    print(f"Clicked next button with selector: {selector}")
                    time.sleep(5)  # Allow page to load
                    return True
                else:
                    print(f"Next button is not clickable or visible with selector: {selector}")
                    continue
            except TimeoutException:
                print(f"Timeout for selector: {selector}")
                attempts += 1
                continue
            except Exception as e:
                print(f"An error occurred while trying to click the button: {e}")
                attempts += 1
                continue

        print("No 'Next page' button found using common selectors.")
        return False
    except Exception as e:
        print(f"An error occurred while clicking 'Next page': {e}")
        return False



### Data extraction ###
def extract_data(driver, url, class_name=None):
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Extract base_url (e.g., https://curatorsintl.org)
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Extract details from the first page
    print("Extracting details from the first page...")
    all_data = Extract_data_from_multi_links.extract_data_with_details(driver, soup, base_url)

    # Check for the "Next Page" button and paginate if available
    if has_next_page_button(soup):
        print("Detected 'Next Page' button. Scraping with pagination.")
        all_data.extend(scrape_with_pagination(driver, url, class_name, base_url))
    else:
        print("No 'Next Page' button. Only extracted data from the first page.")

    return all_data


def has_next_page_button(soup):
    print("Entering has_next_page_button...")

    # Try to detect by text matching on 'Next' and 'Next Page'
    next_button = soup.find('a', text=re.compile(r'(Next|Next Page)', re.I))
    if next_button:
        print(f"Next page button found by text: {next_button.text}")
        return True

    # Try to detect by 'aria-label' or 'rel' attribute
    next_button = soup.find('a', {'aria-label': re.compile(r'(Next page|next)', re.I)})
    if next_button:
        print(f"Next page button found by aria-label: {next_button['aria-label']}")
        return True

    # Detect by rel="next" attribute
    next_button = soup.find('a', {'rel': 'next'})
    if next_button:
        print(f"Next page button found by rel attribute: {next_button['rel']}")
        return True

    # Use CSS selectors for common pagination patterns (e.g., buttons or divs with pagination or arrow-like classes)
    next_button = soup.select_one("a[aria-label='Next page'], a.pagination__next, button.pagination__next, a.page-next, a.icon-btn")
    if next_button:
        print(f"Next page button found by CSS selector.")
        return True

    # Check for buttons or divs that may contain a next button or icon
    next_button = soup.find('button', {'aria-label': re.compile(r'(Next|next)', re.I)}) or \
                  soup.find('div', {'aria-label': re.compile(r'(Next|next)', re.I)})
    if next_button:
        print(f"Next page button found within a button or div.")
        return True

    print("No next page button found")
    return False



def detect_format(soup):
    if soup.find('table'):
        return 'table'
    elif soup.find('ul') or soup.find('ol'):
        return 'list'
    elif soup.find('div'):
        return 'div'
    else:
        return 'unknown'


def fetch_next_page_requests(soup):
    next_button = soup.find('a', {'aria-label': 'Next page'})
    if not next_button:
        print("No 'Next page' button found.")
        return None

    next_page_url = next_button['href']
    if not next_page_url:
        print("No valid 'Next page' URL found.")
        return None

    try:
        response = requests.get(next_page_url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Failed to fetch the next page: {e}")
        return None



def fetch_next_page_playwright(page):
    next_button = page.query_selector("a[aria-label='Next page']")
    if not next_button:
        print("No 'Next page' button found.")
        return None

    next_button.click()
    page.wait_for_timeout(3000)
    return BeautifulSoup(page.content(), 'html.parser')



async def fetch_next_page_httpx(client, next_page_url):
    try:
        response = await client.get(next_page_url)
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Failed to fetch the next page: {e}")
        return None



