import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
import csv

def api_login_and_scrape(url, email, password, max_page=1):
    """
    Logs in to the given URL and scrapes details, saving HTML files to 'details' folder.
    """
    session = requests.Session()

    # The URL of the login page
    login_url = "https://cinando.com/"

    # Request headers
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Origin': 'https://cinando.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }

    # Get the login page and parse out the CSRF token
    login_page = session.get(login_url)
    soup = BeautifulSoup(login_page.text, 'html.parser')

    # Find the hidden RequestVerificationToken field
    csrf_token = soup.find('input', {'name': '__RequestVerificationToken'})['value']

    login_payload = {
        'Email': email,
        'Password': password,
        '__RequestVerificationToken': csrf_token
    }

    # Send login request
    login_response = session.post(login_url, data=login_payload, headers=headers)

    # Check whether the login is successful
    if login_response.status_code == 200 and "Login" not in login_response.url:
        print("Login successful")

        # Get Cookies from the login response
        cookies = login_response.cookies

        # Initialize pagination parameters
        start = 0
        length = 20
        all_results = []
        current_page = 0

        # Create a directory to store detail files
        output_dir = "details"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        while current_page < max_page:  # Add page limit
            # Prepare load data for API requests
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
            elif 'Film/SearchPostgres' in url:
                payload = {
                    "Start": start,
                    "Length": length,
                    "SortColumn": "id",
                    "SortDir": "desc",
                    "criteria[Query]": "",
                    "criteria[Keyword]": "",
                    "criteria[CountryMain]": False,
                    "criteria[CountryAdvanced]": False,
                    "criteria[AvailabilityAdvanced]": False,
                    "criteria[Market]": 0,
                    "criteria[MarketPremiere]": False,
                    "criteria[Debut]": False,
                    "criteria[MarketStatus]": "",
                    "criteria[HasScreener]": False,
                    "criteria[CurrentPastStatus]": 2,
                    "criteria[Cliste]": "",
                    "criteria[Editable]": False,
                    "DontUpdateLength": False
                }
            elif 'People/Search' in url:
                payload = {
                    "Start": start,
                    "Length": length,
                    "SortColumn": "name",
                    "SortDir": "asc",
                    "criteria[Query]": "",
                    "criteria[Keyword]": "",
                    "criteria[CountryAdvanced]": False,
                    "criteria[CompanyActivityMain]": False,
                    "criteria[PeopleActivityMain]": False,
                    "criteria[Cliste]": "",
                    "criteria[Editable]": False,
                    "criteria[OnsiteOnly]": False,
                    "DontUpdateLength": False
                }
            else:
                print("Unsupported URL type.")
                return

            # Update headers to ensure that the request headers include cookies and CSRF tokens
            session.headers.update(headers)

            # Add retry mechanism
            retry_count = 0
            max_retries = 3

            while retry_count < max_retries:
                response = session.post(url, data=payload, cookies=cookies)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        results = data.get('results', [])

                        if not results:
                            # No more results, break the loop
                            break

                        # Add current results to the list
                        all_results.extend(results)
                        print(f"Fetched {len(results)} results, total: {len(all_results)}")

                        # For each entity, get detailed page
                        for result in results:
                            entity_name = result.get('Name') or result.get('Title', 'Unnamed_Entity')
                            detail_link = result.get('Link', '')
                            if detail_link:
                                # Construct full URL for the detail page
                                detail_url = f"https://cinando.com{detail_link}"
                                detail_headers = headers.copy()
                                detail_headers.update({
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                                    'Upgrade-Insecure-Requests': '1',
                                })

                                # Send GET request to fetch details
                                detail_response = session.get(detail_url, headers=detail_headers, cookies=cookies)
                                if detail_response.status_code == 200:
                                    # Parsing the detail content
                                    detail_page = detail_response.text
                                    # Save the detail HTML to a file
                                    entity_name = entity_name.replace('/', '_').replace(' ', '_')
                                    with open(os.path.join(output_dir, f"details_{entity_name}.html"), 'w',
                                              encoding='utf-8') as file:
                                        file.write(detail_page)
                                    print(f"Details for entity {entity_name} saved to file.")
                                    time.sleep(1)  # Delay to avoid too many requests at once
                                else:
                                    print(
                                        f"Failed to fetch details for {entity_name}: Status code {detail_response.status_code}")

                        # Increment start for next batch and increment page count
                        start += length
                        current_page += 1

                        # Add delay to avoid server overload
                        time.sleep(1)  # Wait 1 second to avoid too frequent requests
                        break

                    except ValueError as e:
                        print(f"Error parsing JSON: {e}")
                        break
                else:
                    retry_count += 1
                    print(f"Request failed, status code {response.status_code}, retry {retry_count}/{max_retries}...")
                    time.sleep(2)  # Wait 2 seconds before retrying

            if retry_count == max_retries:
                print("Unable to retrieve data after multiple retries, skipping this request")
                break

    else:
        print("Login failed")


import os
import csv
from bs4 import BeautifulSoup

def extract_bio_and_image_from_html(directory, output_csv):
    """
    Extract bio and image information from HTML files in the specified directory and save to a CSV file.
    """
    entity_data = []

    # Iterate over all HTML files in the specified directory
    for filename in os.listdir(directory):
        if filename.endswith(".html"):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file, 'html.parser')

                # Find the div containing the entity information
                website_div = soup.find('div', class_='website')
                if website_div:
                    # Determine the page type and find the corresponding div
                    page_entity_div = website_div.find('div', class_=['page-company', 'page-film', 'page-people'])
                    if page_entity_div:
                        # Extract bio information
                        bio_parts = []

                        # Extract address information (more comprehensive)
                        address_div = page_entity_div.find('div', class_='address')
                        if address_div:
                            # Extract all text within the address div, including any nested tags
                            address_text = address_div.get_text(separator=' ', strip=True)
                            bio_parts.append(address_text)

                        # Extract time information
                        time_info_div = soup.find('div', class_='cover__info--cover--clock')
                        if time_info_div:
                            bio_parts.append(time_info_div.get_text(strip=True))

                        # Extract contact links
                        links_div = soup.find('div', class_='links')
                        if links_div:
                            for link in links_div.find_all('a'):
                                bio_parts.append(link.get_text(strip=True))

                        # Extract content information while ignoring address parts
                        content_div = soup.find('div', class_='content')
                        if content_div:
                            # Extract all text within content_div, excluding elements that are within address divs
                            content_text_parts = []
                            for element in content_div.find_all(recursive=False):
                                if not element.find_parent('div', class_='address'):
                                    content_text_parts.append(element.get_text(strip=True))
                            content_text = ' '.join(content_text_parts)
                            if content_text:
                                bio_parts.append(content_text)

                        # Extract tab-content information (ignore if not found)
                        tab_content_div = soup.find('div', class_='tab-content')
                        if tab_content_div:
                            tab_panel_div = tab_content_div.find('div', class_='tab-pane')
                            if tab_panel_div:
                                list_informations = tab_panel_div.find('ul', class_='list-informations')
                                if list_informations:
                                    for li in list_informations.find_all('li'):
                                        sub_ul = li.find('ul')
                                        if sub_ul:
                                            labels = sub_ul.find_all('li')
                                            if len(labels) >= 2:
                                                key = labels[0].get_text(strip=True)
                                                value = labels[1].get_text(strip=True)
                                                bio_parts.append(f"{key}: {value}")

                        # Extract other bio information
                        for tag in page_entity_div.find_all(['p']):
                            if tag.find_parent('div', class_=['address', 'content', 'links', 'tab-content', 'cover__info--cover--clock']):
                                continue
                            bio_parts.append(tag.get_text(strip=True))

                        # Combine bio parts
                        bio = ' '.join(bio_parts) if bio_parts else 'No bio available'

                        # Extract image information
                        image_tag = page_entity_div.find('img')
                        image_url = image_tag['src'] if image_tag else 'No image available'

                        # Append extracted data
                        entity_data.append({
                            'filename': filename,
                            'bio': bio,
                            'image_url': image_url
                        })

    # Write the extracted data to a CSV file
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['filename', 'bio', 'image_url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(entity_data)

    print(f"Successfully extracted bio and image URL for {len(entity_data)} entities and saved to {output_csv}.")



# test
#email = "davidmoreno@72dragons.com"
#password = "DrDragon72!"

#api_login_and_scrape("https://cinando.com/en/Film/SearchPostgres", email, password, max_page=1)

# https://cinando.com/en/Film/SearchPostgres
# https://cinando.com/en/People/Search
# https://cinando.com/en/Company/Search
