import os
import random
import time
import requests
from bs4 import BeautifulSoup
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import datetime
import sqlite3

# Initialize the SQLite database
DB_NAME = "pause_status.db"
def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pause_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        website TEXT NOT NULL,
        unpause_time TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def reset_database():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print("Database reset completed. Reinitializing...")
    initialize_database()

def add_pause_status(website, pause_duration):
    unpause_time = (datetime.datetime.now() + pause_duration).isoformat()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pause_status (website, unpause_time) VALUES (?, ?)", (website, unpause_time))
    conn.commit()
    conn.close()
    print(f"Added pause for {website} until {unpause_time}")


def handle_timeout(website):
    print(f"Request timed out, entering pause state...")
    pause_duration = datetime.timedelta(hours=1)
    add_pause_status(website, pause_duration)
    print(f"Pause status stored, waiting for {pause_duration} before resuming execution.")
    exit()

def check_pause_status(website):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT unpause_time FROM pause_status WHERE website = ?", (website,))
    result = cursor.fetchone()
    conn.close()
    if result:
        unpause_time = datetime.datetime.fromisoformat(result[0])
        if datetime.datetime.now() >= unpause_time:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pause_status WHERE website = ?", (website,))
            conn.commit()
            conn.close()
            print(f"Pause for {website} has ended, resuming operations.")
            return False  # stop pause
        else:
            print(f"Still in pause for {website} until {unpause_time}")
            return True  # still pause
    return False  # No pause state


def handle_cooldown(website):
    pause_duration = datetime.timedelta(hours=1)
    add_pause_status(website, pause_duration)
    while check_pause_status(website):
        print("Checking if cooldown has ended...")
        time.sleep(300)  # Check every 5 min

def api_login_and_scrape_company(url, email, password, max_page=1):
    reset_database()
    session = requests.Session()
    login_url = "https://cinando.com/"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.8',
        'Origin': 'https://cinando.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }
    login_page = session.get(login_url)
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_token = soup.find('input', {'name': '__RequestVerificationToken'})['value']
    login_payload = {
        'Email': email,
        'Password': password,
        '__RequestVerificationToken': csrf_token
    }
    login_response = session.post(login_url, data=login_payload, headers=headers)

    if login_response.status_code == 200 and "Login" not in login_response.url:
        print("Login successful")
        cookies = login_response.cookies
        start = 0
        length = 20
        current_page = 0
        output_dir = "company_details"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        while current_page < max_page:
            if 'Company/Search' in url:
                payload = {
                    "Start": start,
                    "Length": length,
                    "SortColumn": "name",
                    "SortDir": "asc",
                    "criteria[Query]": "",
                    "criteria[Keyword]": "",
                    "criteria[CountryAdvanced]": False,
                    "criteria[ActivityMain]": False,
                    "criteria[OtherTerritories]": "",
                    "criteria[Cliste]": "",
                    "criteria[Editable]": False,
                    "DontUpdateLength": False
                }
            else:
                print("Unsupported URL type.")
                return

            session.headers.update(headers)
            retry_count = 0
            max_retries = 5

            while retry_count < max_retries:
                try:
                    if check_pause_status(url):
                        print("Currently paused, waiting...")
                        time.sleep(300)
                        continue

                    response = session.post(url, data=payload, cookies=cookies, timeout=60)

                    if response.status_code == 200:
                        data = response.json()
                        results = data.get('results', [])

                        if not results:
                            break

                        print(f"Fetched {len(results)} results")

                        for result in results:
                            company_name = result.get('Name', None)
                            detail_link = result.get('Link', None)

                            if company_name and detail_link:
                                print(f"Processing company: {company_name}")
                                bio, image_url, website_url = extract_company_bio_image_website(detail_link, session, headers, cookies)
                                social_links = search_social_media_links(company_name, url)

                                with open('company_data.csv', 'a', newline='', encoding='utf-8') as csvfile:
                                    fieldnames = ['Company Name', 'Bio', 'Image URL', 'Website URL', 'Facebook', 'Instagram']
                                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                                    if csvfile.tell() == 0:
                                        writer.writeheader()

                                    writer.writerow({
                                        'Company Name': company_name,
                                        'Bio': bio,
                                        'Image URL': image_url,
                                        'Website URL': website_url,
                                        'Facebook': social_links.get('Facebook', 'N/A'),
                                        'Instagram': social_links.get('Instagram', 'N/A')
                                    })

                        start += length
                        current_page += 1
                        time.sleep(random.uniform(10, 15))
                        break

                    else:
                        retry_count += 1
                        print(f"Request failed, status code {response.status_code}, retry {retry_count}/{max_retries}...")
                        time.sleep(random.uniform(10, 15))

                except requests.exceptions.Timeout:
                    handle_timeout(url)

            if retry_count == max_retries:
                print("Unable to retrieve data after multiple retries, entering cooldown period.")
                handle_timeout(url)

    else:
        print("Login failed")



def extract_company_bio_image_website(detail_link, session, headers, cookies):
    # Extract bio, image, and website link from the detail page
    detail_url = f"https://cinando.com{detail_link}"
    detail_headers = headers.copy()
    detail_headers.update({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,'
                  'image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Upgrade-Insecure-Requests': '1',
    })

    detail_response = session.get(detail_url, headers=detail_headers, cookies=cookies, timeout=60)
    if detail_response.status_code == 200:
        soup = BeautifulSoup(detail_response.text, 'html.parser')

        # Extract bio information
        bio_parts = []

        # Extract bio from content div
        content_div = soup.find('div', class_='content')
        if content_div:
            content_text_parts = [element.get_text(strip=True) for element in content_div.find_all(recursive=False) if element.get_text(strip=True)]
            bio_parts.extend(content_text_parts)

        # Combine bio parts and remove duplicates
        bio = ' '.join(set(bio_parts)) if bio_parts else 'No bio available'

        # Extract image information
        image_tag = soup.find('img')
        image_url = image_tag['src'] if image_tag else 'No image available'

        # Extract website link from bio information
        website_url = 'No website available'
        bio_links = content_div.find_all('a', href=True) if content_div else []
        for link in bio_links:
            href = link['href']
            if 'http' in href:
                website_url = href
                break

        return bio, image_url, website_url

    else:
        print(f"Failed to fetch details page for link: {detail_link}")
        return 'No bio available', 'No image available', 'No website available'


def search_social_media_links(company_name, website):
    # Set up Selenium WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    social_links = {'Facebook': 'N/A', 'Instagram': 'N/A'}

    try:
        platforms = ['facebook', 'instagram']
        for platform in platforms:
            query = f"{company_name} {platform} site:{platform}.com"
            driver.get("https://www.google.com/")
            search_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q")))
            search_box.clear()
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)

            results = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.yuRUbf a")))
            if results:
                link = results[0].get_attribute("href")
                if platform in link:
                    social_links[platform.capitalize()] = link
            else:
                print(f"No social media links found for {platform}.")

            time.sleep(random.uniform(10, 15))

    except Exception as e:
        print(f"Error when searching for social media links: {e}")
        handle_cooldown(website)

    finally:
        driver.quit()

    return social_links


if __name__ == "__main__":
    test_url = "https://cinando.com/en/Company/Search"
    test_email = "davidmoreno@72dragons.com"
    test_password = "DrDragon72!"
    max_page = 5

    api_login_and_scrape_company(test_url, test_email, test_password, max_page=max_page)
