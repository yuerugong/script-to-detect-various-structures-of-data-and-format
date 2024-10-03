import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


def clean_unnecessary_elements(soup):
    """Remove unnecessary elements from the soup."""
    # Define elements to be removed
    tags_to_remove = ['header', 'aside', 'footer', 'form', 'modal fade', 'sidebar',
                      'search-lst--top', 'search-lst--filters', 'pre-header', 'fixed-header']

    # Remove all specified tags and classes
    for tag in tags_to_remove:
        for element in soup.find_all(class_=tag):
            element.decompose()

    # Remove elements by ID
    if banner := soup.find(id='SearchBanner'):
        banner.decompose()

    return soup


def extract_data_with_details(driver, soup, base_url):
    print("Extracting detailed data from the page...", flush=True)

    # Clean unnecessary elements from the soup
    soup = clean_unnecessary_elements(soup)

    # Check if <main> or class="main" exists for targeted data extraction
    main_content = soup.find('main') or soup.find(class_='main')

    if main_content:
        extracted_data = extract_from_anchor_tags(main_content, base_url)
    else:
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
    try:
        response = requests.get(person_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        bio = extract_bio_from_main_or_fallback(soup)
        image = extract_images_from_main_or_fallback(soup, person_url)

        return bio, image
    except requests.RequestException:
        return None, None


def extract_bio_from_main_or_fallback(soup):
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
    images = []

    # Clean the soup
    soup = clean_unnecessary_elements(soup)

    main_content = soup.find('main') or soup.find(class_='main')
    img_tags = main_content.find_all('img') if main_content else soup.find_all('img')

    for img_tag in img_tags:
        image = img_tag.get('src')
        if image and not image.startswith('data:'):
            images.append(urljoin(person_url, image))
    return images


def filter_content(data):
    seen = set()
    filtered_data = []
    for item in data:
        clean_item = re.sub(r'\[.*?\]', '', item['name'])
        if clean_item not in seen:
            filtered_data.append(item)
            seen.add(clean_item)
    return filtered_data
