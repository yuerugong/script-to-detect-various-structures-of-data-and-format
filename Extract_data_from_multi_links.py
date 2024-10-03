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
        image = extract_images_from_main_or_fallback(soup, person_url)

        return bio, image

    except requests.RequestException as e:
        print(f"Failed to retrieve bio and image for {person_url}: {e}", flush=True)
        return None, None


def extract_bio_from_main_or_fallback(soup):
    """
    Extract bio information including name, job title, and phone numbers.
    """
    bio = ""

    # Remove any unnecessary elements globally before processing
    for form in soup.find_all('form'):
        form.decompose()
    for footer_element in soup.find_all(class_='footer'):
        footer_element.decompose()
    for modal_fade in soup.find_all(class_='modal fade'):
        modal_fade.decompose()

    # Try to find <main> tag or class="main"
    main_content = soup.find('main') or soup.find(class_='main')

    if main_content:
        bio_paragraphs = main_content.find_all('p')
    else:
        bio_paragraphs = soup.find_all('p')

    if bio_paragraphs:
        # Join the text from all <p> tags to form the full bio
        bio = "\n".join([p.get_text(separator="\n", strip=True) for p in bio_paragraphs])

    # Extract additional bio information from other sections
    name_tag = soup.find('div', class_='item--name')
    if name_tag:
        name = name_tag.find('a').get_text(strip=True)
        bio += "\n" + name

    # Extract job title and role
    function_tag = soup.find('div', class_='item--function')
    if function_tag:
        function = function_tag.get_text(strip=True)
        bio += "\n" + function

    # Extract additional titles/roles (e.g., Production, Servicing)
    title_tag = soup.find('div', class_='item--title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        bio += "\n" + title

    # Extract phone numbers
    phones_tag = soup.find('div', class_='item--phones')
    if phones_tag:
        tel_tag = phones_tag.find('div', class_='tel')
        mobile_tag = phones_tag.find('div', class_='mobile')
        if tel_tag:
            bio += "\nTel: " + tel_tag.get_text(strip=True)
        if mobile_tag:
            bio += "\nMobile: " + mobile_tag.get_text(strip=True)

    return bio.strip()


def extract_images_from_main_or_fallback(soup, person_url):
    """
    Extracts all image URLs from the page.
    Checks for images in <main> or globally, and collects 'src' attributes.
    """
    images = []

    # Remove unnecessary elements
    for footer_element in soup.find_all(class_='footer'):
        footer_element.decompose()
    for preheader_element in soup.find_all(class_='pre-header'):
        preheader_element.decompose()
    for fixed_header_element in soup.find_all(class_='fixed-header'):
        fixed_header_element.decompose()
    for sidebar_element in soup.find_all(class_='sidebar'):
        sidebar_element.decompose()
    for search_top_element in soup.find_all(class_='search-lst--top'):
        search_top_element.decompose()
    for search_filters_element in soup.find_all(class_='search-lst--filters'):
        search_filters_element.decompose()

    # Remove any element with id="SearchBanner"
    search_banner_element = soup.find(id='SearchBanner')
    if search_banner_element:
        search_banner_element.decompose()

    # Try to find all images in <main> or globally
    main_content = soup.find('main') or soup.find(class_='main')

    if main_content:
        print("Found <main> tag or class='main'. Searching for images...", flush=True)
        img_tags = main_content.find_all('img')
    else:
        print("No <main> tag or class='main' found. Searching globally for images...", flush=True)
        img_tags = soup.find_all('img')

    # Iterate over all <img> tags and extract their 'src' attributes
    for img_tag in img_tags:
        # Try to get the 'src' attribute (Base64 image data or URL)
        image = img_tag.get('src')

        # If image src is a relative URL, convert it to an absolute URL
        if image and not image.startswith('data:'):
            image = urljoin(person_url, image)

        # Append the image link to the list
        if image:
            images.append(image)

    return images


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
