from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def get_selenium_options():
    options = Options()
    # options.add_argument("--headless=new") # simulates normal visual rendering
    ## options for docker
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-data-dir=/tmp/chrome-user-data")
    ##
    options.add_argument("--disable-gpu") # help prevent graphical glitches
    options.add_argument("--window-size=1920,1080")
    # set a common user-agent to avoid being detected as a bot/scraper
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    return options

def get_imdb_reviews(url):
    options = get_selenium_options()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    try:
        # wait until the page is fully loaded (presence of <body> tag)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        # try to accept the cookie banner if it appears
        try:
            print("########### Searching reviews ###########")
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="accept-button"]'))
            )
            driver.execute_script("arguments[0].click();", cookie_button)
            print("### Cookie banner accepted. ###")
            time.sleep(1)
        except:
            print("### Cookie banner not present or already accepted. ###")

        print("### Attempting to click the show 'All' button... ###")

        try:
            # look for all buttons on the page
            buttons = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'button.ipc-see-more__button'))
            )

            if len(buttons) < 2:
                print("### Show All button NOT found. ###")
            else:
                second_button = buttons[1]

                # scroll into view and click it once to load more reviews
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", second_button)
                time.sleep(1)
                second_button.click()
                print("### Clicked the second button. ###")
                time.sleep(3)  # Wait for content to load

                print("### Starting scroll + wait cycle... ###")
                x = 5
                for i in range(x):
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", second_button)
                    print(f"### Scroll {i+1}/{x} on second button. ###")
                    time.sleep(3)

        except (TimeoutException, ElementClickInterceptedException) as e:
            print(f"### Error while clicking or scrolling: {type(e).__name__} ###")


    except Exception as e:
        print(f"### Error during initial page load: {e} ###")

    # parse the fully loaded page with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "lxml")
    driver.quit()
    # extract all review elements from the HTML
    articles = soup.select("article.user-review-item")
    reviews = []
    # parse each review and extract title, comment, rating, and date
    for article in articles:
        title = article.select_one("h3.ipc-title__text")
        comment = article.select_one("div.ipc-html-content-inner-div[role='presentation']")
        rating = article.select_one("span.ipc-rating-star--rating")
        date = article.select_one("li.ipc-inline-list__item.review-date")

        reviews.append({
            "title": title.get_text(strip=True) if title else "N/A",
            "comment": comment.get_text(strip=True) if comment else "N/A",
            "rating": rating.get_text(strip=True) if rating else None,
            "date": date.get_text(strip=True) if date else "N/A"
        })

    return reviews

def search_imdb_titles(query):
    search_url = f"https://www.imdb.com/find/?q={query}&s=tt&exact=true"

    options = get_selenium_options()

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(search_url)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        try:
            print("########### Searching titles ###########")
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="accept-button"]'))
            )
            driver.execute_script("arguments[0].click();", cookie_button)
            print("### Cookie banner accepted. ###")
            time.sleep(1)
        except:
            print("### Cookie banner not present or already accepted. ###")

        try:
            more_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.ipc-see-more__button'))
            )
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", more_button)
            time.sleep(1)
            more_button.click()
            time.sleep(2)
        except TimeoutException:
                print("### Show All button NOT found. ###")

        soup = BeautifulSoup(driver.page_source, "lxml")

    finally:
        driver.quit()

    results = []
    items = soup.select("li.ipc-metadata-list-summary-item")  # IMDb search result items

    for item in items:
        # extract the main title and link
        title_el = item.select_one("a.ipc-metadata-list-summary-item__t")
        title = title_el.get_text(strip=True) if title_el else "N/A"
        link = f"https://www.imdb.com{title_el['href']}" if title_el and title_el.has_attr("href") else "N/A"

        # extract additional metadata: year, category, actors...
        spans = item.select("span.ipc-metadata-list-summary-item__li.ipc-btn--not-interactable")
        infos = [span.get_text(strip=True) for span in spans]
        year = infos[0] if len(infos) > 0 else "N/A"
        other_info = infos[1:] if len(infos) > 1 else []

        results.append({
            "title": title,
            "year": year,
            "other_info": other_info,
            "url": link
        })

    return results
