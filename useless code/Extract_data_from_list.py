from bs4 import BeautifulSoup
import requests


def extract_list_data(soup, class_name=None):
    # Finds the div for the specified class name, or all divs
    divs = soup.find_all('div', class_=class_name) if class_name else soup.find_all('div')

    if not divs:
        print("No div elements found on the page.")
        return []

    data = []
    for index, div in enumerate(divs):
        print(f"Processing div element {index + 1}")
        div_data = {}

        # Iterate over direct child elements to extract text
        for child in div.find_all(recursive=False):
            text = child.get_text(strip=True)
            if text:
                div_data.setdefault(child.name, []).append(text)

        # If there is data, add it to the result list
        if div_data:
            data.append(div_data)

    return data


if __name__ == "__main__":
    url = input("Please enter the URL of the page you want to scrape: ")
    class_name = input("Please enter the class name of the div (if you know it, leave it blank otherwise): ")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract all data
    data = extract_list_data(soup, class_name if class_name else None)
    print("Data scraped:", data)
