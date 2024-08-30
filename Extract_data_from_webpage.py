from bs4 import BeautifulSoup


def extract_table_data(file_path):
    # read file content
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    soup = BeautifulSoup(content, 'html.parser')

    # find table
    table = soup.find('table')
    if not table:
        print("No table found on the page.")
        return

    # get headers
    headers = []
    for th in table.find_all('th'):
        headers.append(th.text.strip())
    print("Table Headers:", headers)

    # get table content
    rows = []
    for tr in table.find_all('tr')[1:]:  # Skip the header row
        cells = tr.find_all('td')
        row = [cell.text.strip() for cell in cells]
        rows.append(row)

    print("Table Body:")
    for row in rows:
        print(row)


# Test with local html file
file_path = 'sample page .html'
extract_table_data(file_path)
