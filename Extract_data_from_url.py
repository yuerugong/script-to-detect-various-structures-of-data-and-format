def extract_table_data(soup):
    tables = soup.find_all('table')
    if not tables:
        print("No tables found on the page.")
        return []

    all_rows = []
    for index, table in enumerate(tables):
        print(f"Processing Table {index + 1}...")
        rows = table.find_all('tr')
        if not rows:
            print("No rows found in the table.")
            continue

        print(f"Found {len(rows)} rows in Table {index + 1}.")
        headers = [th.text.strip() for th in rows[0].find_all(['th', 'td'])]
        print(f"Headers: {headers}")

        for tr in rows[1:]:
            cells = tr.find_all('td')
            if not cells:
                print("No cells found in this row, skipping.")
                continue

            row_data = {headers[i]: cells[i].text.strip() for i in range(len(cells))}
            print(f"Extracted row: {row_data}")
            all_rows.append(row_data)

    if all_rows:
        print(f"Extracted data from {len(all_rows)} rows.")
        return all_rows
    else:
        print("No data extracted from the tables.")
        return None
