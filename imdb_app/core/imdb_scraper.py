from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, InvalidArgumentException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin, urlparse
import re
import os
import json
import time
import uuid

def get_selenium_options():
    options = Options()
    ## options for docker
    if os.getenv("SELENIUM_HEADLESS", "1").lower() in {"1", "true", "yes"}:
        options.add_argument("--headless=new")  # simulates normal visual rendering
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-data-dir=/tmp/chrome-user-data-{uuid.uuid4().hex}")
    ##
    options.add_argument("--disable-gpu") # help prevent graphical glitches
    options.add_argument("--window-size=1920,1080")
    # set a common user-agent to avoid being detected as a bot/scraper
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    return options

def _is_valid_http_url(url):
    if not isinstance(url, str):
        return False

    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

def _extract_imdb_title_id(url):
    if not _is_valid_http_url(url):
        return None

    match = re.search(r"/title/(tt\d+)", url)
    return match.group(1) if match else None

def _normalize_title_text(text):
    if not text:
        return ""
    cleaned = re.sub(r"^\s*View title page for\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def _extract_year_from_text(text):
    if not text:
        return "N/A"
    match = re.search(r"\b(?:19|20)\d{2}\b", text)
    return match.group(0) if match else "N/A"

def _normalize_for_match(text):
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()

def _score_title_match(query, title):
    q = _normalize_for_match(query)
    t = _normalize_for_match(title)

    if not q or not t:
        return -1
    if t == q:
        return 100
    if t.startswith(q):
        return 80
    if q in t:
        return 60

    q_words = set(q.split())
    t_words = set(t.split())
    if not q_words:
        return 0

    overlap = len(q_words & t_words)
    return overlap

def _extract_title_text_from_anchor(anchor):
    if not anchor:
        return ""

    text = anchor.get_text(strip=True)
    if text:
        return _normalize_title_text(text)

    aria_label = (anchor.get("aria-label") or "").strip()
    if aria_label:
        return _normalize_title_text(aria_label)

    title_attr = (anchor.get("title") or "").strip()
    if title_attr:
        return _normalize_title_text(title_attr)

    img = anchor.find("img")
    if img:
        alt = (img.get("alt") or "").strip()
        if alt:
            return _normalize_title_text(alt)

    return ""

def _pick_title_anchor(item):
    if not item:
        return None

    candidates = item.select('a[href*="/title/tt"]')
    if not candidates:
        return None

    # Prefer the first link that actually carries human-readable title text.
    for anchor in candidates:
        if _extract_title_text_from_anchor(anchor):
            return anchor

    # Fallback to first title link (often poster link).
    return candidates[0]

def _extract_reviews_from_json_ld(soup):
    extracted = []
    seen = set()
    scripts = soup.select("script[type='application/ld+json']")

    for script in scripts:
        raw = (script.string or script.get_text() or "").strip()
        if not raw:
            continue

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        nodes = payload if isinstance(payload, list) else [payload]
        for node in nodes:
            if not isinstance(node, dict):
                continue

            reviews = node.get("review")
            if not reviews:
                continue
            if isinstance(reviews, dict):
                reviews = [reviews]

            for review in reviews:
                if not isinstance(review, dict):
                    continue

                title_text = _normalize_title_text(review.get("name", "N/A"))
                body_text = str(review.get("reviewBody", "N/A")).strip()
                date_text = str(review.get("datePublished", "N/A")).strip()

                rating_value = None
                rating_obj = review.get("reviewRating")
                if isinstance(rating_obj, dict):
                    rating_value = rating_obj.get("ratingValue")
                if rating_value is not None:
                    rating_value = str(rating_value).strip()

                key = (title_text, body_text, rating_value, date_text)
                if key in seen:
                    continue
                seen.add(key)

                if body_text == "N/A" and title_text == "N/A":
                    continue

                extracted.append({
                    "title": title_text or "N/A",
                    "comment": body_text or "N/A",
                    "rating": rating_value,
                    "date": date_text or "N/A",
                })

    return extracted

def build_imdb_reviews_url(title_url):
    title_id = _extract_imdb_title_id(title_url)
    if not title_id:
        return None
    return f"https://www.imdb.com/title/{title_id}/reviews/"

def _try_click_cookie_banner(driver, timeout=3):
    selectors = [
        (By.CSS_SELECTOR, '[data-testid="accept-button"]'),
        (By.CSS_SELECTOR, "#onetrust-accept-btn-handler"),
        (By.XPATH, '//button[normalize-space()="Accept"]'),
        (By.XPATH, '//button[normalize-space()="Accetta"]'),
        (By.XPATH, '//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "accept")]'),
        (By.XPATH, '//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "accetta")]'),
        (By.XPATH, '//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "agree")]'),
    ]

    def _click_first_match():
        for by, selector in selectors:
            try:
                btn = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((by, selector))
                )
                driver.execute_script("arguments[0].click();", btn)
                return True, selector
            except Exception:
                continue
        return False, None

    clicked, selector = _click_first_match()
    if clicked:
        print(f"### Cookie banner accepted via selector: {selector} ###")
        return True

    # Some CMPs render banner inside an iframe.
    for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
        try:
            driver.switch_to.frame(iframe)
            clicked, selector = _click_first_match()
            if clicked:
                print(f"### Cookie banner accepted inside iframe via selector: {selector} ###")
                driver.switch_to.default_content()
                return True
        except Exception:
            pass
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

    return False

def get_imdb_reviews(url):
    if not _is_valid_http_url(url):
        print(f"### Invalid reviews URL: {url} ###")
        return []

    options = get_selenium_options()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(url)
    except InvalidArgumentException:
        print(f"### Selenium rejected URL: {url} ###")
        driver.quit()
        return []

    try:
        # wait until the page is fully loaded (presence of <body> tag)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        # try to accept the cookie banner if it appears
        print("########### Searching reviews ###########")
        if _try_click_cookie_banner(driver, timeout=2):
            time.sleep(1)
        elif _try_click_cookie_banner(driver, timeout=2):
            time.sleep(1)
        else:
            print("### Cookie banner not present or already accepted. ###")

        print("### Attempting to click the show 'All' button... ###")

        review_css = "article.user-review-item, div.review-container, div.lister-item.mode-detail.imdb-user-review, [data-testid='review-container']"

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

        try:
            WebDriverWait(driver, 12).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, review_css)) > 0 or "No user reviews" in d.page_source
            )
        except TimeoutException:
            print("### Timed out waiting for review containers. ###")

    except Exception as e:
        print(f"### Error during initial page load: {e} ###")

    # parse the fully loaded page with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "lxml")
    driver.quit()
    # extract all review elements from the HTML
    articles = soup.select("article.user-review-item, div.review-container, div.lister-item.mode-detail.imdb-user-review, [data-testid='review-container']")
    reviews = []
    seen_reviews = set()
    # parse each review and extract title, comment, rating, and date
    for article in articles:
        title = article.select_one("h3.ipc-title__text, a.title")
        comment = article.select_one(
            "div.ipc-html-content-inner-div[role='presentation'], "
            "div.ipc-html-content-inner-div, "
            "[data-testid='review-overflow'], "
            "div.text.show-more__control"
        )
        rating = article.select_one(
            "span.ipc-rating-star--rating, "
            "span.ipc-rating-star, "
            "span.rating-other-user-rating span"
        )
        date = article.select_one("li.ipc-inline-list__item.review-date, span.review-date")

        title_text = _normalize_title_text(title.get_text(strip=True)) if title else "N/A"
        comment_text = comment.get_text(" ", strip=True) if comment else "N/A"
        rating_text = rating.get_text(strip=True) if rating else None
        date_text = date.get_text(strip=True) if date else "N/A"

        review_key = (title_text, comment_text, rating_text, date_text)
        if review_key in seen_reviews:
            continue
        seen_reviews.add(review_key)

        if comment_text == "N/A" and title_text == "N/A":
            continue

        reviews.append({
            "title": title_text,
            "comment": comment_text,
            "rating": rating_text,
            "date": date_text
        })

    if not reviews:
        fallback_reviews = _extract_reviews_from_json_ld(soup)
        if fallback_reviews:
            print(f"### Fallback JSON-LD reviews extracted: {len(fallback_reviews)} ###")
            return fallback_reviews

    return reviews

def search_imdb_titles(query):
    if not query or not str(query).strip():
        return []

    encoded_query = quote_plus(str(query).strip())
    search_url = f"https://www.imdb.com/find/?q={encoded_query}&s=tt&exact=true"

    options = get_selenium_options()

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(search_url)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("########### Searching titles ###########")
        if _try_click_cookie_banner(driver, timeout=2):
            time.sleep(1)
        elif _try_click_cookie_banner(driver, timeout=2):
            time.sleep(1)
        else:
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

        # Wait for at least one title link before parsing HTML.
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, 'a[href*="/title/tt"]')) > 0
            )
        except TimeoutException:
            print("### Timed out waiting for title links. ###")

        soup = BeautifulSoup(driver.page_source, "lxml")

    finally:
        driver.quit()

    results = []
    seen_title_ids = set()
    items = soup.select("li.ipc-metadata-list-summary-item, li.find-result-item")

    for item in items:
        title_el = _pick_title_anchor(item)
        if not title_el:
            continue

        href = title_el.get("href")
        link = urljoin("https://www.imdb.com", href) if href else None
        title_id = _extract_imdb_title_id(link)
        if not title_id or title_id in seen_title_ids:
            continue
        seen_title_ids.add(title_id)

        title = _normalize_title_text(_extract_title_text_from_anchor(title_el)) or "N/A"
        spans = item.select("span.ipc-metadata-list-summary-item__li, span.find-result-item__meta")
        infos = [span.get_text(strip=True) for span in spans if span.get_text(strip=True)]
        item_text = item.get_text(" ", strip=True)
        year = _extract_year_from_text(" ".join(infos) or item_text)
        other_info = infos[1:] if len(infos) > 1 else []

        results.append({
            "title": title,
            "year": year,
            "other_info": other_info,
            "url": f"https://www.imdb.com/title/{title_id}/"
        })

    # Last-resort fallback if card containers changed.
    if not results:
        anchors = soup.select('a[href*="/title/tt"]')
        for a in anchors:
            href = a.get("href")
            link = urljoin("https://www.imdb.com", href) if href else None
            title_id = _extract_imdb_title_id(link)
            if not title_id or title_id in seen_title_ids:
                continue
            seen_title_ids.add(title_id)

            title = _normalize_title_text(_extract_title_text_from_anchor(a)) or "N/A"
            results.append({
                "title": title,
                "year": "N/A",
                "other_info": [],
                "url": f"https://www.imdb.com/title/{title_id}/"
            })

    if results:
        # Keep IMDb order as secondary key, but prioritize query relevance.
        indexed = list(enumerate(results))
        indexed.sort(
            key=lambda pair: (
                _score_title_match(query, pair[1].get("title", "")),
                -pair[0],
            ),
            reverse=True,
        )
        results = [item for _, item in indexed]

    return results
