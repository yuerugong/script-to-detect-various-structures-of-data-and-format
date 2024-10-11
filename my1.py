import requests
from bs4 import BeautifulSoup


def api_login_and_scrape(url, email, password, country_id=None):
    session = requests.Session()

    # The URL of the login page
    login_url = "https://cinando.com/"
    # request headers
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
        print("登录成功")

        # Get Cookies from the login response
        cookies = login_response.cookies

        # Prepare load data for API requests
        payload = {
            "Start": 0,
            "Length": 20,
            "SortColumn": "name",
            "SortDir": "asc",
            "criteria[Query]": "",
            "criteria[CountriesGroups][ID]": country_id,
            "criteria[Keyword]": "",
            "criteria[CountryAdvanced]": False,
            "criteria[CompanyActivityMain]": False,
            "criteria[PeopleActivityMain]": False,
            "criteria[Editable]": False,
            "criteria[OnsiteOnly]": False,
            "DontUpdateLength": False
        }

        # Update headers to ensure that the request headers include cookies and CSRF tokens
        session.headers.update(headers)

        # Send data requests with cookies at login
        response = session.post(url, data=payload, cookies=cookies)

        print(f"Response status code: {response.status_code}")
        print("Response content:")
        print(response.text)  # Output the original response content

        # If the response is JSON, try parsing it
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Successfully fetched {data['resultsCount']} results.")
            except ValueError as e:
                print(f"Error parsing JSON: {e}")
        else:
            print(f"Failed to fetch data: Status code {response.status_code}")
    else:
        print("login failed")


# test
email = "davidmoreno@72dragons.com"
password = "DrDragon72!"
country_id = 4  # add filter for “MIDDLE EAST & CENTRAL ASIA”

api_login_and_scrape("https://cinando.com/en/People/Search", email, password, country_id)
