# Cinando Scraping Project

## File Description

### 1. Ignore the `useless code` Folder  
- The code in this folder is **not related to the Cinando website** and can be ignored.

---

### 2. `cinando.py`  
#### Function:  
`cinando.py` is designed to work with the following **three Cinando-related websites** to extract the **bio information** and **image link** from each detail page:  
- [Cinando Film Search](https://cinando.com/en/Film/SearchPostgres)  
- [Cinando People Search](https://cinando.com/en/People/Search)  
- [Cinando Company Search](https://cinando.com/en/Company/Search)

#### Usage:  
- The script can be used in combination with `app.py` to interact with a local web interface for data scraping operations.

---

### 3. `Cinando_IMDB_film.py` and `selenium_search.py`  
#### Function:  
This is a **two-part script** targeting the **[Cinando Film Search](https://cinando.com/en/Film/SearchPostgres)** website:  
- **Step 1**: Run `Cinando_IMDB_film.py` to fetch each film's **bio information** and **image link**.  
- **Step 2**: Use the output of `Cinando_IMDB_film.py` as input for `selenium_search.py` to retrieve **IMDb information** as well as **Facebook (FB)** and **Instagram (Ins)** links.  

#### Output:  
The final output is saved in a CSV file named `collected_data_3.csv`.

---

### 4. `Cinando_IMDB_film_company.py`  
#### Function:  
`Cinando_IMDB_film_company.py` is specifically designed for the **[Cinando Company Search](https://cinando.com/en/Company/Search)** website.  
- It extracts each company's **bio information** and **image link**.  
- Additionally, it retrieves the company's **official website link** along with **Facebook (FB)** and **Instagram (Ins)** links.

---

## Notes for Usage  
- Before running the scripts, ensure that all necessary dependencies (e.g., `selenium`, `requests`) are installed.  
- Use the scripts responsibly, comply with the target website's terms of use, and control the request frequency to avoid triggering anti-scraping mechanisms.
