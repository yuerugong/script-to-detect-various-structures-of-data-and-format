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

            print(f"Original href: {href}")

            if href.startswith(('http://', 'https://')):
                # href -> absolute url
                full_url = href
            else:
                # href -> relative url
                full_url = urljoin(base_url, href)

            print(f"Full URL: {full_url}")

            data.append({
                'name': a.get_text(strip=True),
                'link': full_url
            })

    return data


def extract_bio_and_image(person_url):
    """
    Extracts the bio and image from an individual profile page, generalized to handle multiple webpage structures.
    """
    try:
        print(f"Fetching data for: {person_url}", flush=True)

        # Fetch the person's profile page
        response = requests.get(person_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the bio (from all <p> tags, fallback if no specific container is available)
        bio = ""
        bio_paragraphs = soup.find_all('p')
        if bio_paragraphs:
            # Join the text from all <p> tags to form the full bio
            bio = "\n".join([p.get_text(strip=True) for p in bio_paragraphs])

        # Extract the image (from <img> tags)
        image = ""
        img_tag = soup.find('img')
        if img_tag:
            # First, try to get the 'data-srcset' attribute (the attribute you're interested in)
            srcset = img_tag.get('data-srcset')
            if srcset:
                # Extract all URLs and widths
                srcset_urls = [entry.split(" ")[0] for entry in srcset.split(",")]
                # Select the largest image (the last one in the list)
                image = srcset_urls[-1]
            else:
                # Fallback to 'data-src' or 'src'
                image = img_tag.get('data-src') or img_tag.get('src')

            # If image src is relative, convert to absolute
            if image:
                image = urljoin(person_url, image)

        print(f"Bio: {bio}")
        print(f"Image: {image}")

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
        else:
            print(f"Duplicate detected, skipping: {clean_item}")
    return filtered_data
