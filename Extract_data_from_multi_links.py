import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


def extract_data_with_details(driver, soup, base_url):
    print("Extracting detailed data from the page...", flush=True)

    # List to store extracted data
    extracted_data = []

    extracted_data = extract_from_anchor_tags(soup, base_url)

    # Iterate over each person's profile link to extract bio and image
    for person in extracted_data:
        bio, image = extract_bio_and_image(person['link'])
        person['bio'] = bio
        person['image'] = image

    # Filter out duplicates
    filtered_data = filter_content(extracted_data)

    return filtered_data


def extract_from_anchor_tags(soup, base_url):
    data = []

    # Iterate over all 'a' tags
    for a in soup.find_all('a'):
        href = a.get('data-uw-original-href') or a.get('href')
        if href and a.get_text(strip=True):  # Ensure it's a valid link with text
            full_url = urljoin(base_url, href)

            # Add the name and the (potentially full) link to the data
            data.append({
                'name': a.get_text(strip=True),
                'link': full_url
            })

    return data


def extract_bio_and_image(person_url):
    """
    Extracts the bio and image from an individual profile page.
    """
    try:
        print(f"Fetching data for: {person_url}", flush=True)

        # Fetch the person's profile page
        response = requests.get(person_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the bio (from <p> tags)
        bio = ""
        bio_paragraphs = soup.find_all('p')
        if bio_paragraphs:
            bio = "\n".join([p.get_text(strip=True) for p in bio_paragraphs])

        # Extract the image (from <img> tags)
        image = ""
        img_tag = soup.find('img')
        if img_tag and img_tag.get('src'):
            image = img_tag['src']
            # If image src is relative, convert to absolute
            image = urljoin(person_url, image)

        return bio, image

    except requests.RequestException as e:
        print(f"Failed to retrieve bio and image for {person_url}: {e}", flush=True)
        return None, None


def filter_content(data):
    seen = set()
    filtered_data = []
    for item in data:
        # First, remove unnecessary content inside brackets
        clean_item = re.sub(r'\[.*?\]', '', item['name'])
        # Then, check for duplicates
        if clean_item not in seen:
            filtered_data.append(item)
            seen.add(clean_item)
    return filtered_data
