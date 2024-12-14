import os
import time
import requests
from bs4 import BeautifulSoup
import csv
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import unicodedata


def standardize_title(title):
    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9 :,\'\"-]', '', title).strip().lower()


def get_imdb_urls(movie_title, omdb_api_key):
    # Standardize the movie title to ensure consistency in the OMDb API search
    standardized_title = standardize_title(movie_title)
    omdb_url = f"http://www.omdbapi.com/?s={standardized_title}&apikey={omdb_api_key}"
    response = requests.get(omdb_url)

    if response.status_code == 200:
        # Parse the JSON response from the OMDb API
        omdb_data = response.json()

        if omdb_data.get('Response') == 'True':
            # Extract all matching IMDb URLs from the OMDb search results
            imdb_urls = []
            for item in omdb_data.get('Search', []):
                if item.get('Title').lower() == movie_title.lower():
                    imdb_id = item.get('imdbID', '')
                    if imdb_id:
                        imdb_urls.append(f"https://www.imdb.com/title/{imdb_id}")
            return imdb_urls

        # Print a message if no matching movie was found in the OMDb data
        print(f"No matching movie found in OMDb data: {movie_title}")
    else:
        # Print an error message if the OMDb API request failed
        print(f"OMDb API request failed with status code: {response.status_code}")

    # Return an empty list if no URLs were found or the request failed
    return []



def get_omdb_data(movie_title, movie_year, director, omdb_api_key):
    standardized_title = standardize_title(movie_title)
    omdb_url = f"http://www.omdbapi.com/?t={standardized_title}&y={movie_year}&apikey={omdb_api_key}"
    response = requests.get(omdb_url)

    if response.status_code == 200:
        omdb_data = response.json()
        # Check if the year and director match to ensure accuracy
        if (omdb_data.get('Response') == 'True' and
                omdb_data.get('Year') == str(movie_year) and
                (director.lower() in omdb_data.get('Director', '').lower())):
            return omdb_data
        else:
            print(f"OMDb data does not match year or director for {movie_title}. Skipping enrichment.")
            return None
    else:
        print(f"Failed to retrieve OMDb data for {movie_title}. Status code: {response.status_code}")
        return None


def api_login_and_scrape(url, email, password, max_page=1):
    """
    登录 Cinando 并爬取电影数据，同时通过 OMDb API 查询 IMDb 信息。
    电影名称用于查询 IMDb URL，而其他 IMDb 数据依赖电影名称、年份和导演的匹配逻辑。
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
        current_page = 0

        # Create a directory to store detail files
        output_dir = "details"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        omdb_api_key = "1c87756d"  # Set OMDb API key

        while current_page < max_page:  # Add page limit
            # Prepare load data for API requests
            if 'Film/SearchPostgres' in url:
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

                        print(f"Fetched {len(results)} results")

                        # For each entity, get detailed page and enrich with OMDb data
                        for result in results:
                            movie_title = result.get('Title', None)
                            movie_year = result.get('Year', None)
                            director = result.get('Director', None)

                            if movie_title:
                                print(f"Processing movie: {movie_title}")

                                # Query IMDb URLs based only on the movie title
                                imdb_urls = get_imdb_urls(movie_title, omdb_api_key)
                                result['imdb_url'] = "; ".join(imdb_urls) if imdb_urls else 'Not Found'

                                # Query detailed IMDb data with title, year, and director
                                omdb_data = get_omdb_data(movie_title, movie_year, director, omdb_api_key)
                                if omdb_data:
                                    result['imdb_rating'] = omdb_data.get('imdbRating', 'Not Found')
                                    result['imdb_director'] = omdb_data.get('Director', 'Not Found')
                                    result['imdb_cast'] = omdb_data.get('Actors', 'Not Found')
                                    result['genre'] = omdb_data.get('Genre', 'Not Found')
                                    result['runtime'] = omdb_data.get('Runtime', 'Not Found')
                                    result['language'] = omdb_data.get('Language', 'Not Found')
                                    result['awards'] = omdb_data.get('Awards', 'Not Found')
                                else:
                                    result['imdb_rating'] = 'Not Found'
                                    result['imdb_director'] = 'Not Found'
                                    result['imdb_cast'] = 'Not Found'
                                    result['genre'] = 'Not Found'
                                    result['runtime'] = 'Not Found'
                                    result['language'] = 'Not Found'
                                    result['awards'] = 'Not Found'

                                # Save results to CSV
                                with open('collected_data.csv', 'a', newline='', encoding='utf-8') as csvfile:
                                    fieldnames = ['Title', 'Year', 'Director', 'bio', 'image_url', 'imdb_rating',
                                                  'imdb_director', 'imdb_cast', 'genre', 'runtime', 'language', 'awards',
                                                  'imdb_url', 'similar_1', 'similar_2', 'similar_3']
                                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                                    if csvfile.tell() == 0:
                                        writer.writeheader()

                                    bio, image_url = extract_bio_and_image(result.get('Link', ''), session, headers,
                                                                           cookies)

                                    writer.writerow({
                                        'Title': movie_title,
                                        'Year': movie_year,
                                        'Director': director,
                                        'bio': bio,
                                        'image_url': image_url,
                                        'imdb_rating': result.get('imdb_rating', 'Not Found'),
                                        'imdb_director': result.get('imdb_director', 'Not Found'),
                                        'imdb_cast': result.get('imdb_cast', 'Not Found'),
                                        'genre': result.get('genre', 'Not Found'),
                                        'runtime': result.get('runtime', 'Not Found'),
                                        'language': result.get('language', 'Not Found'),
                                        'awards': result.get('awards', 'Not Found'),
                                        'imdb_url': result.get('imdb_url', 'Not Found'),
                                        'similar_1': '',
                                        'similar_2': '',
                                        'similar_3': ''
                                    })

                        # Increment start for next batch and increment page count
                        start += length
                        current_page += 1

                        # Add delay to avoid server overload
                        time.sleep(1)
                        break

                    except ValueError as e:
                        print(f"Error parsing JSON: {e}")
                        break
                else:
                    retry_count += 1
                    print(f"Request failed, status code {response.status_code}, retry {retry_count}/{max_retries}...")
                    time.sleep(2)

            if retry_count == max_retries:
                print("Unable to retrieve data after multiple retries, skipping this request")
                break

    else:
        print("Login failed")



def extract_bio_and_image(detail_link, session, headers, cookies):
    # Extract bio and image from the detail page
    detail_url = f"https://cinando.com{detail_link}"
    detail_headers = headers.copy()
    detail_headers.update({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,'
                  'image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Upgrade-Insecure-Requests': '1',
    })

    detail_response = session.get(detail_url, headers=detail_headers, cookies=cookies)
    if detail_response.status_code == 200:
        soup = BeautifulSoup(detail_response.text, 'html.parser')

        # Extract bio information
        bio_parts = []

        # Extract time information
        time_info_div = soup.find('div', class_='cover__info--cover--clock')
        if time_info_div:
            bio_parts.append(time_info_div.get_text(strip=True))

        # Extract all the content in the content
        content_div = soup.find('div', class_='content')
        if content_div:
            content_text_parts = []
            for element in content_div.find_all(recursive=False):
                element_text = element.get_text(strip=True)
                if element_text:
                    content_text_parts.append(element_text)
            content_text = ' '.join(content_text_parts)
            if content_text and content_text not in bio_parts:
                bio_parts.append(content_text)

        # Extract festival & awards information (for film)
        award_items_div = soup.find('div', class_='award--items')
        if award_items_div:
            for item_div in award_items_div.find_all('div', class_='item'):
                title_div = item_div.find('div', class_='item--title')
                content_div = item_div.find('div', class_='item--content')

                title_text = title_div.get_text(strip=True) if title_div else None
                content_text = content_div.get_text(strip=True) if content_div else ''

                if title_text:
                    bio_parts.append(f"{title_text}: {content_text}")

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
                                if key and value:
                                    bio_parts.append(f"{key}: {value}")

        # Extract other bio information
        page_entity_div = soup.find('div', class_=['page-company', 'page-film', 'page-people'])
        if page_entity_div:
            for tag in page_entity_div.find_all(['p']):
                if tag.find_parent('div',
                                   class_=['address', 'content', 'links', 'tab-content', 'cover__info--cover--clock']):
                    continue
                tag_text = tag.get_text(strip=True)
                if tag_text and tag_text not in bio_parts:
                    bio_parts.append(tag_text)

        # Combine bio parts and remove duplicates
        bio = ' '.join(set(bio_parts)) if bio_parts else 'No bio available'

        # Extract image information
        image_tag = page_entity_div.find('img')
        image_url = image_tag['src'] if image_tag else 'No image available'

        return bio, image_url

    else:
        print(f"Failed to fetch details page for link: {detail_link}")
        return 'No bio available', 'No image available'


def identify_similar_productions_with_imdb(input_csv, output_csv, omdb_api_key):
    # Read data
    productions = []
    with open(input_csv, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            productions.append(row)

    # Extract existing movie bio information
    production_bios = [production['bio'] for production in productions]
    imdb_bios = []
    imdb_titles = []
    imdb_directors = []
    imdb_actors = []

    # Fetch IMDb data for similarity analysis
    for production in productions:
        movie_title = production['Title']
        if movie_title:
            omdb_data = get_omdb_data(
                movie_title,
                production.get('Year', None),
                production.get('Director', None),
                omdb_api_key
            )
            if omdb_data:
                imdb_bios.append(omdb_data.get('Plot', ''))
                imdb_titles.append(omdb_data.get('Title', 'Unknown'))
                imdb_directors.append(omdb_data.get('Director', 'Unknown'))
                imdb_actors.append(omdb_data.get('Actors', 'Unknown'))
            else:
                imdb_bios.append('')
                imdb_titles.append('Unknown')
                imdb_directors.append('Unknown')
                imdb_actors.append('Unknown')

    # Combine existing data with IMDb data
    all_bios = production_bios + imdb_bios
    vectorizer = TfidfVectorizer().fit_transform(all_bios)
    similarity_matrix = cosine_similarity(vectorizer)

    # Find the most similar IMDb movie for each production
    for i, production in enumerate(productions):
        similarity_scores = list(enumerate(similarity_matrix[i, len(production_bios):]))
        similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)

        # Filter out IMDb movies with high similarity scores
        top_similar = []
        for idx, score in similarity_scores:
            if score > 0:
                # Match by movie title, director, or actors; skip if no match
                imdb_title = imdb_titles[idx]
                imdb_director = imdb_directors[idx]
                imdb_actors_list = imdb_actors[idx]

                if (production['Title'].lower() in imdb_title.lower() or
                        production['Director'].lower() in imdb_director.lower() or
                        any(actor.lower() in imdb_actors_list.lower() for actor in
                            production.get('imdb_cast', '').split(','))):
                    top_similar.append(imdb_title)

            # Keep only the top 3 matches
            if len(top_similar) >= 3:
                break

        # If no valid match, keep it empty
        production['similar_1'] = top_similar[0] if len(top_similar) > 0 else ''
        production['similar_2'] = top_similar[1] if len(top_similar) > 1 else ''
        production['similar_3'] = top_similar[2] if len(top_similar) > 2 else ''

    # Write the updated data to the output CSV file
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Title', 'Year', 'Director', 'bio', 'image_url', 'imdb_rating',
                      'imdb_director', 'imdb_cast', 'genre', 'runtime', 'language', 'awards',
                      'imdb_url', 'similar_1', 'similar_2', 'similar_3']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(productions)
    print(f"Data matching is complete and the result has been saved to {output_csv}")


if __name__ == "__main__":
    test_url = "https://cinando.com/en/Film/SearchPostgres"
    test_email = "davidmoreno@72dragons.com"
    test_password = "DrDragon72!"
    max_page = 1

    api_login_and_scrape(test_url, test_email, test_password, max_page=max_page)
    identify_similar_productions_with_imdb('collected_data.csv', 'collected_data_2.csv', "1c87756d")