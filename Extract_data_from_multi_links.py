import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


def extract_data_with_details(driver, soup, base_url):
    print("Extracting detailed data from the page...", flush=True)

    # First, remove all <header> tags and their content
    for header in soup.find_all('header'):
        header.decompose()  # Remove <header> and all its content

    # List to store extracted data
    extracted_data = []

    # Check if <main> or class="main" exists for targeted data extraction
    main_content = soup.find('main') or soup.find(class_='main')

    if main_content:
        print("Found <main> tag or class='main'. Extracting data within main content...", flush=True)
        extracted_data = extract_from_anchor_tags(main_content, base_url)
    else:
        print("No <main> tag or class='main' found. Extracting data from the entire page...", flush=True)
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

        # Extract the bio from <main> or fallback to <p> tags
        bio = extract_bio_from_main_or_fallback(soup)

        # Extract the image from <main> or fallback to the global search
        image = extract_image_from_main_or_fallback(soup, person_url)

        return bio, image

    except requests.RequestException as e:
        print(f"Failed to retrieve bio and image for {person_url}: {e}", flush=True)
        return None, None


def extract_bio_from_main_or_fallback(soup):
    """
    First checks for <main> tags or class="main" to search for bio information.
    If no such tag or class is found, fallback to extracting text from <p> tags.
    Removes any <span> and <form> tags and their content from the entire soup.
    """
    bio = ""

    # First, globally remove all <form> and <span> tags before processing
    for form in soup.find_all('form'):
        form.decompose()  # Completely remove all <form> tags and their content
    for span in soup.find_all('span'):
        span.decompose()  # Completely remove all <span> tags and their content
    for span in soup.find_all('footer'):
        span.decompose()  # Completely remove all <footer> tags and their content

    # Try to find <main> tag or class="main"
    main_content = soup.find('main') or soup.find(class_='main')

    if main_content:
        print("Found <main> tag or class='main'. Searching within the main content for bio...", flush=True)
        bio_paragraphs = main_content.find_all('p')
    else:
        print("No <main> tag or class='main' found. Searching globally for bio...", flush=True)
        bio_paragraphs = soup.find_all('p')

    if bio_paragraphs:
        # Join the text from all <p> tags to form the full bio
        bio = "\n".join([p.get_text(strip=True) for p in bio_paragraphs])

    return bio


def extract_image_from_main_or_fallback(soup, person_url):
    """
    First checks for <main> tags or class="main" to search for an image.
    If no such tag or class is found, fallback to data-srcset, data-src, or src attributes.
    """
    image = ""

    # Try to find <main> tag or class="main"
    main_content = soup.find('main') or soup.find(class_='main')

    if main_content:
        print("Found <main> tag or class='main'. Searching within the main content...", flush=True)
        img_tag = main_content.find('img')
    else:
        print("No <main> tag or class='main' found. Searching globally for the image...", flush=True)
        img_tag = soup.find('img')

    if img_tag:
        # Try to get the 'data-srcset' attribute first
        srcset = img_tag.get('data-srcset')
        if srcset:
            # Extract all URLs and select the largest image (the last one in the list)
            srcset_urls = [entry.split(" ")[0] for entry in srcset.split(",")]
            image = srcset_urls[-1]
        else:
            # Fallback to 'data-src' or 'src'
            image = img_tag.get('data-src') or img_tag.get('src')

        # If image src is relative, convert to absolute
        if image:
            image = urljoin(person_url, image)

    return image


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
