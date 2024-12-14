import requests
import csv
import time


def google_search(query, api_key, cse_id):
    """
    Perform a Google Custom Search API query for the specified query string.
    """
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': query,
        'key': api_key,
        'cx': cse_id,
        'num': 10  # Retrieve the top 10 results
    }
    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Google Search API request failed: Status Code {response.status_code}")
        return None


def extract_social_media_links(search_results):
    """
    Extract Facebook and Instagram links from Google search results.
    """
    facebook_link = None
    instagram_link = None

    if search_results:
        for item in search_results.get('items', []):
            link = item.get('link', '')
            if 'facebook.com' in link and not facebook_link:
                facebook_link = link
            if 'instagram.com' in link and not instagram_link:
                instagram_link = link

            # Exit early if both links are found
            if facebook_link and instagram_link:
                break

    return facebook_link, instagram_link


def enrich_with_social_links(input_csv, output_csv, google_api_key, google_cse_id, max_queries=100):
    """
    Use Google Search to find Facebook and Instagram links for each entry.
    """
    enriched_data = []
    query_count = 0

    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            # Check if necessary fields exist
            title = row.get('Title', '').strip()
            director = row.get('Director', '').strip()

            if not director or not title:
                print(f"Skipping invalid data row: {row}")
                continue

            # Generate the query string using the director's name and movie title
            query = f"{director} {title} site:facebook.com OR site:instagram.com"
            print(f"Searching: {query}")

            # Check if the query count has exceeded the daily free limit
            if query_count >= max_queries:
                print("Reached the daily free query limit. Stopping search.")
                break

            # Call Google API and extract social media links
            search_results = google_search(query, google_api_key, google_cse_id)
            facebook_link, instagram_link = extract_social_media_links(search_results)

            # Add the new data to the row
            row['facebook_link'] = facebook_link if facebook_link else 'Not Found'
            row['instagram_link'] = instagram_link if instagram_link else 'Not Found'
            enriched_data.append(row)

            # Increment the query count
            query_count += 1

            # Delay to avoid hitting API rate limits
            time.sleep(1)

    # Save the updated data to a new CSV file
    with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
        fieldnames = list(enriched_data[0].keys())  # Dynamically get column names
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_data)

    print(f"Data processing complete. Results saved to {output_csv}")


if __name__ == "__main__":
    # Input and output files
    input_csv = 'collected_data_with_3similar.csv'  # Your input CSV file
    output_csv = 'collected_data_with_API.csv'  # Output file

    # Google API Key and Custom Search Engine ID
    google_api_key = "AIzaSyBr2KP97smNOuLDemgpVvNGjWa_GZb7-fY"  # Replace with your Google API Key
    google_cse_id = "b511cf43b927c49aa"  # Replace with your Custom Search Engine ID

    # Execute the data enrichment process
    enrich_with_social_links(input_csv, output_csv, google_api_key, google_cse_id)
