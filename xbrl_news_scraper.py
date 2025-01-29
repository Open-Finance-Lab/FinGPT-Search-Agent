from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

debug = True

class XBRLNewsScraper:
    def __init__(self):
        self.url = "https://www.xbrl.org/news/"
        options = Options()
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-gpu")
        options.add_argument("--headless")

        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    def go_to_news(self):
        self.driver.get(self.url)

    def get_news_articles(self):
        articles_data = []
        try:
            # Wait until news articles are present
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.entryPost'))
            )

            # Locate each article container
            articles = self.driver.find_elements(By.CSS_SELECTOR, 'div.entryPost')
            for article in articles:
                try:
                    # Title & Link
                    title_element = article.find_element(By.CSS_SELECTOR, 'h2.entry-title a')
                    title = title_element.text.strip()
                    link = title_element.get_attribute('href')

                    # Author & Date
                    # Example text: "By Editor on December 1, 2024"
                    author_element = article.find_element(By.CSS_SELECTOR, 'p.author')
                    author_text = author_element.text.strip()
                    # Extract date by splitting on 'on '
                    # Result should look like: ["By Editor", "December 1, 2024"]
                    date = None
                    if 'on ' in author_text:
                        date = author_text.split('on ', 1)[1]

                    # Summary
                    # The summary appears in the next <p> after p.author that is not the 'Read more' link
                    # We can find all paragraphs in the article and pick the first after p.author that isn't the author line or 'Read more'
                    paragraphs = article.find_elements(By.CSS_SELECTOR, 'div.post p')
                    # paragraphs[0] should be author line, paragraphs[1] should be summary based on snippet
                    # We'll do a simple approach: 
                    # The first <p> after p.author should be the summary (based on the provided snippet)
                    summary = None
                    if len(paragraphs) > 1:
                        summary = paragraphs[1].text.strip()

                    articles_data.append({
                        "title": title,
                        "link": link,
                        "date": date,
                        "summary": summary
                    })

                except Exception as inner_e:
                    if debug:
                        print("Error scraping a single article:", inner_e)

        except Exception as e:
            if debug:
                print("Error scraping news articles:", e)

        return articles_data

    def close(self):
        self.driver.quit()

if __name__ == "__main__":
    scraper = XBRLNewsScraper()
    scraper.go_to_news()
    news_items = scraper.get_news_articles()
    for item in news_items:
        print(item)
    scraper.close()
