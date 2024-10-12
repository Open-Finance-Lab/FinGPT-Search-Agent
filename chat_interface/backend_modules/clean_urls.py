"""
Takes an array of urls, goes through each one, then sift through this HTML data
to get the actual article contents as a nice string.

This should return a list of maps, where the key is the URL and the value
is the text in a reasonably formatted manner.
"""
'''
def clean_urls(urls:list) -> list:
    pass
'''


import requests
from bs4 import BeautifulSoup

def clean_urls(urls: list) -> list:
    results = []
    
    for url in urls:
        try:
            # Fetch the HTML content
            response = requests.get(url)
            response.raise_for_status()  # Raise an error if the request was not successful
            
            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract relevant text from the HTML - you can adjust the tags you extract based on the structure of the page
            article_text = ''
            for paragraph in soup.find_all('p'):  # Here, we are looking for <p> tags which usually contain main text
                article_text += paragraph.get_text() + "\n"
            
            # Add the URL and its corresponding text to the results
            results.append({url: article_text.strip()})
        
        except requests.exceptions.RequestException as e:
            # Handle exceptions like connection issues or invalid URLs
            print(f"Error fetching {url}: {e}")
            results.append({url: "Error fetching content"})
    
    return results

# Example usage
urls = ["https://www.bloomberg.com", "https://finance.yahoo.com"]
cleaned_data = clean_urls(urls)
for data in cleaned_data:
    print(data)
