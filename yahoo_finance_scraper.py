from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Code is based off https://brightdata.com/blog/how-tos/scrape-yahoo-finance-guide

debug = True  

class YahooFinanceDataScraper:

    def __init__(self):
        self.url = "https://finance.yahoo.com"
        options = Options()
        # These options need to be set so there is no handshake failed error for the protocol
        options.add_argument("--ignore-certificate-errors")
        # Laptop does not have a dedicated gpu
        options.add_argument("--disable-gpu") 
        # Disables UI to reduce additional overhead when scraping 
        options.add_argument("--headless")

        # Drivers for selenium to interact with google chrome
        # Note: this looks at the current version of Google Chrome installed on machine to find drivers
        # Creates chrome browser instance for selenium to interact with
        self.driver = webdriver.Chrome(service = ChromeService(ChromeDriverManager().install()), options = options)

    def go_to_category(self, stock):
        url = f"{self.url}/quote/{stock}"
        self.driver.get(url)

    def scrape_subcategory(self, stock, field, special = False):
        try:
            if not special:
                # Code below waits until html elements are rendered before beginning the scraping process
                element = WebDriverWait(self.driver, 10).until(
                    # This needs to be passed into selenium to scrape a specific part of the CSS 
                    # This can be retrieved by simply inspecting the yahoo finance page 
                    # The fin-streamer tag is a container for the stock price data, selenium finds the fin-streamer element for the specified stock
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, f'fin-streamer[data-symbol = "{stock}"][data-field = "{field}"]')
                    )
                )
            
            else:
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        # Note, {field} must be enclosed in strings to match the exact css element on yahoo finance
                        (By.CSS_SELECTOR, f'li:has(span[title = "{field}"]) span.value')
                    )
                )

            return element.text 

        
        except:
            if debug:
                print(f"Error in scraping {stock}'s {field}")
            pass 

    def scrape_stock(self, stock):
        self.go_to_category(stock)

        data = {
            "stock_symbol": stock,
            "stock_current_price": self.scrape_subcategory(stock, "regularMarketPrice"),
            "stock_previous_close": self.scrape_subcategory(stock, "regularMarketPreviousClose"),
            "stock_open": self.scrape_subcategory(stock, "regularMarketOpen"),
            "stock_bid": self.scrape_subcategory(stock, "Bid", True),
            "stock_ask": self.scrape_subcategory(stock, "Ask", True), 
            "stock_day's_range": self.scrape_subcategory(stock, "Day's Range", True),
            "stock_52_week_range": self.scrape_subcategory(stock, "52 Week Range", True),
            "stock_volume": self.scrape_subcategory(stock, "regularMarketVolume"),
            "stock_avg_volume": self.scrape_subcategory(stock, "averageVolume"),
            "stock_market_cap": self.scrape_subcategory(stock, "Market Cap (intraday)", True),
            "stock_beta": self.scrape_subcategory(stock, "Beta (5Y Monthly)", True),
            "stock_pe_ratio": self.scrape_subcategory(stock, "trailingPE"),
            "stock_forward_dividend_and_yield": self.scrape_subcategory(stock, "Forward Dividend & Yield", True),
            "stock_1_year_target_estimate": self.scrape_subcategory(stock, "targetMeanPrice")
        }

        return data 

    
    def close(self):
        # Simply quits the driver and releases resources
        self.driver.quit()


if __name__ == "__main__":
    scraper = YahooFinanceDataScraper()
    result = scraper.scrape_stock("AAPL")
    print(result)
    scraper.close()
        

