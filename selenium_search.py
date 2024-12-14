# This script uses Cinando_IMDB_film.py as predecessor code

import csv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time


def setup_driver():
    # Set headless browser options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # Initialize WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def find_social_media_links(person_name):
    driver = setup_driver()
    search_query = f"{person_name} site:facebook.com OR site:instagram.com"

    try:
        # Use Google to search for the person's Facebook and Instagram links
        driver.get("https://www.google.com")
        search_box = driver.find_element(By.NAME, "q")
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)

        # Wait for search results to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "search")))

        # Get links from the search results
        social_links = []
        results = driver.find_elements(By.CSS_SELECTOR, "div.yuRUbf a")
        for result in results:
            link = result.get_attribute("href")
            if "facebook.com" in link or "instagram.com" in link:
                social_links.append(link)
            if len(social_links) >= 2:  # Get up to two links
                break

        return social_links if social_links else ["No social media links found"]
    except (NoSuchElementException, TimeoutException) as e:
        print(f"Error finding social media links: {e}")
        return ["No social media links found"]
    finally:
        driver.quit()


def update_csv_with_social_links(input_csv, output_csv):
    # Read CSV data
    productions = []
    with open(input_csv, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            productions.append(row)

    # Find social media links for each relevant person
    for production in productions:
        person_name = production.get('Director', None)
        if person_name:
            print(f"Searching social media links for: {person_name}")
            social_links = find_social_media_links(person_name)
            if 'facebook.com' in social_links[0]:
                production['facebook_link'] = social_links[0]
                production['instagram_link'] = social_links[1] if len(social_links) > 1 and 'instagram.com' in \
                                                                  social_links[1] else 'Not Found'
            else:
                production['instagram_link'] = social_links[0]
                production['facebook_link'] = social_links[1] if len(social_links) > 1 and 'facebook.com' in \
                                                                 social_links[1] else 'Not Found'
            production['instagram_link'] = social_links[1] if len(social_links) > 1 else ''
        else:
            production['facebook_link'] = 'Not Found'
            production['instagram_link'] = 'Not Found'

    # Write updated data to a new CSV file
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Title', 'Year', 'Director', 'bio', 'image_url', 'imdb_rating',
                      'imdb_director', 'imdb_cast', 'genre', 'runtime', 'language', 'awards',
                      'imdb_url', 'similar_1', 'similar_2', 'similar_3', 'facebook_link', 'instagram_link']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(productions)
    print(f"Social media links have been added and saved to {output_csv}")


if __name__ == "__main__":
    input_csv = 'collected_data_2.csv'
    output_csv = 'collected_data_3.csv'
    update_csv_with_social_links(input_csv, output_csv)

