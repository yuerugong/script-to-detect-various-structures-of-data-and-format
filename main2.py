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
import Extract_data_from_url
import Extract_data_from_list

def detect_format(soup):
    if soup.find('table'):
        return 'table'
    elif soup.find('ul') or soup.find('ol'):
        return 'list'
    elif soup.find('div'):
        return 'div'
    else:
        return 'unknown'

def extract_data(soup, class_name=None):
    format_type = detect_format(soup)
    print(f"Detected format: {format_type}")

    if format_type == 'table':
        table_data = Extract_data_from_url.extract_table_data(soup)
        if table_data:
            return table_data
    elif format_type in ['list', 'div']:
        list_data = Extract_data_from_list.extract_list_data(soup, class_name)
        if list_data:
            return list_data
    else:
        print("Unknown format")
    return None

def find_and_click_next_button(driver, max_attempts=12):
    try:
        next_button_selectors = [
            "//button[@aria-label='Goto next page']",
            "//button[@data-testid='next-page-button']",
            "//button[contains(@class, 'icon-btn')]",
            "//a[contains(text(), 'Next')]",
            "//a[contains(text(), 'next')]",
            "//a[contains(@aria-label, 'Next')]",
            "//a[contains(@class, 'next')]",
            "//button[contains(text(), 'Next')]",
            "//button[contains(text(), 'next')]",
            "//button[contains(@aria-label, 'Next')]",
            "//button[contains(@class, 'next')]",
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
                    EC.element_to_be_clickable((By.XPATH, selector))
                )

                if next_button and next_button.is_enabled() and next_button.is_displayed():
                    driver.execute_script("arguments[0].click();", next_button)
                    print(f"Clicked next button with selector: {selector}")
                    time.sleep(5)
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

def scrape_with_pagination(driver, url, max_pages=10):
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    initial_url = driver.current_url
    pages_scraped = 0
    all_data = []
    last_page_source = ""
    first_page_data = None
    visited_urls = set()

    while pages_scraped < max_pages:
        print(f"Scraping page {pages_scraped + 1}")
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        data = extract_data(soup)
        if data:
            print(f"Data extracted from page {pages_scraped + 1}")

            # 如果是第一页的数据，将其保存到first_page_data
            if pages_scraped == 0:
                first_page_data = data
                all_data.extend(data)  # 仅在第一页时添加数据
            else:
                # 检查当前页面的数据与第一页的数据的相似度
                common_data_count = sum(1 for item in data if item in first_page_data)
                if common_data_count / len(first_page_data) > 0.7:
                    print("Detected similar content as the first page. Exiting.")
                    break
                else:
                    all_data.extend(data)  # 仅在内容不相似时添加数据

        current_page_source = driver.page_source
        if current_page_source == last_page_source:
            print("Page content did not change after clicking 'Next page'. Exiting.")
            break

        last_page_source = current_page_source

        if driver.current_url in visited_urls:
            print(f"URL {driver.current_url} has already been visited. Exiting to prevent loop.")
            break

        visited_urls.add(driver.current_url)

        if not find_and_click_next_button(driver):
            print("Failed to find or click 'Next page' button.")
            break

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)

        if driver.current_url == initial_url:
            print("Page did not change after clicking 'Next page'. Exiting.")
            break

        initial_url = driver.current_url
        pages_scraped += 1

    print("No more pages to scrape.")
    return all_data



def selenium_scrape(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    try:
        driver = webdriver.Chrome(executable_path="/Users/gongyueru/Downloads/chromedriver-mac-arm64/chromedriver",
                                  options=options)
        data = scrape_with_pagination(driver, url)
        driver.quit()
        return data
    except WebDriverException as e:
        print(f"Failed with Selenium: {e}")
        return None


def scrape_with_pagination_generic(soup, get_next_page_url, fetch_page_content, max_pages=1):
    all_data = []
    initial_content = soup.get_text()
    pages_scraped = 0
    visited_urls = set()

    while pages_scraped < max_pages:
        page_data = extract_data(soup)
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


def requests_beautifulsoup_scrape(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        all_data = scrape_with_pagination_generic(soup, fetch_next_page_requests)
        return all_data
    except Exception as e:
        print(f"Failed with Requests + BeautifulSoup: {e}")
        return None


def fetch_next_page_playwright(page):
    next_button = page.query_selector("a[aria-label='Next page']")
    if not next_button:
        print("No 'Next page' button found.")
        return None

    next_button.click()
    page.wait_for_timeout(3000)
    return BeautifulSoup(page.content(), 'html.parser')


def playwright_scrape(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)
            soup = BeautifulSoup(page.content(), 'html.parser')
            all_data = scrape_with_pagination_generic(soup, lambda _: fetch_next_page_playwright(page))
            browser.close()
            return all_data
    except Exception as e:
        print(f"Failed with Playwright: {e}")
        return None


async def fetch_next_page_httpx(client, next_page_url):
    try:
        response = await client.get(next_page_url)
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Failed to fetch the next page: {e}")
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

            all_data = await scrape_with_pagination_generic(soup, fetch_next_page_wrapper)
            return all_data
    except Exception as e:
        print(f"Failed with httpx + Asyncio + BeautifulSoup: {e}")
        return None


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

