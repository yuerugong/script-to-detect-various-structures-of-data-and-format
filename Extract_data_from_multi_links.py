import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


def extract_data_with_details(driver, soup, base_url):
    print("Extracting detailed data from the page...", flush=True)

    # remove all <header> and <aside> tags and their content
    for element in soup.find_all(['header', 'aside', 'footer']):
        element.decompose()  # Remove <header> and <aside> and all their content

    # Remove any element with class="footer"
    for footer_element in soup.find_all(class_='footer'):
        footer_element.decompose()  # Remove all elements with class="footer"

    # Remove any element with class="pre-header"
    for preheader_element in soup.find_all(class_='pre-header'):
        preheader_element.decompose()  # Remove all elements with class="pre-header"

    # Remove any element with class="fixed-header"
    for fixed_header_element in soup.find_all(class_='fixed-header'):
        fixed_header_element.decompose()  # Remove all elements with class="fixed-header"

    # Remove any element with class="sidebar"
    for sidebar_element in soup.find_all(class_='sidebar'):
        sidebar_element.decompose()  # Remove all elements with class="sidebar"

    # Remove any element with class="search-lst--top"
    for search_top_element in soup.find_all(class_='search-lst--top'):
        search_top_element.decompose()  # Remove all elements with class="search-lst--top"

    # Remove any element with class="search-lst--filters"
    for search_filters_element in soup.find_all(class_='search-lst--filters'):
        search_filters_element.decompose()  # Remove all elements with class="search-lst--filters"

    # Remove any element with id="SearchBanner"
    search_banner_element = soup.find(id='SearchBanner')
    if search_banner_element:
        search_banner_element.decompose()  # Remove element with id="SearchBanner"

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
    seen_links = set()  # To store unique links

    # Iterate over all 'a' tags
    for a in soup.find_all('a'):
        href = a.get('data-uw-original-href') or a.get('href')
        rel = a.get('rel', [])  # Get the 'rel' attribute, defaulting to an empty list if not present

        # Filter out links with rel="nofollow"
        if href and 'nofollow' not in rel:
            # Make the URL absolute if it's relative
            if href.startswith(('http://', 'https://')):
                full_url = href
            else:
                full_url = urljoin(base_url, href)

            # Skip if the link has already been processed
            if full_url in seen_links:
                continue

            # Check if the link has a title attribute
            link_text = a.get('title')  # Prefer using the title attribute

            # If no title, fall back to the anchor text
            if not link_text:
                link_text = a.get_text(strip=True)

            # Skip common "Read More" type links or empty text links
            if not link_text or link_text.lower() in ["read more", "click here", "learn more", "report this?",
                                                      "register", "terms and conditions", "privacy policy",
                                                      "find out more"]:
                continue

            # Print the extracted URL and text (for debugging)
            print(f"Extracted URL: {full_url}, Text: {link_text}")

            # Store the link and its associated text
            data.append({
                'name': link_text,
                'link': full_url
            })

            # Mark this URL as seen
            seen_links.add(full_url)

    return data



def extract_relevant_text(anchor_tag):
    """
    Extracts the most relevant and meaningful text from an anchor tag.
    If the <a> tag itself does not have visible text, it tries to extract from nearby elements.
    """
    link_text = anchor_tag.get_text(strip=True)

    # If <a> tag text is empty, try to find text from nearby <h1>, <h2>, <h3>, <p>, or <span> tags
    if not link_text:
        for sibling in anchor_tag.find_all_previous(['h1', 'h2', 'h3', 'h4'], limit=1):
            link_text = sibling.get_text(strip=True)
            if link_text:
                break

    return link_text


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
