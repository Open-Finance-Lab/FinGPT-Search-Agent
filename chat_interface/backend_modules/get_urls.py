'''
takes as input an array of key words, combines them into a single string,
and then searches the web to find 1-5 urls that match the most with
the keywords provided.

The URLs should be returned as a list of strings.

The main websites we will be searching for now will be bloomberg, yahoo finance, and 
google search. If you want, you can use other sites in your implementation
'''
from googlesearch import search
from get_keywords import get_keywords

''' previous function that Doan commented out (please test the function at the bottom to see if it aligns with what you are looking for)
def get_urls(query) -> list:
    List_Urls = []
    for url in search(query, num=10, stop=10, pause =0):
        List_Urls.append(url)
'''

from googlesearch import search
from get_keywords import get_keywords  # Import the get_keywords function

def get_urls(user_input: str, model_name: str = "gpt-3.5-turbo", num_urls: int = 5) -> list:
    # Step 1: Extract keywords from user input using GPT-3.5/4
    keywords = get_keywords(user_input, model_name)

    # Combine the list of keywords into a query string
    query = " ".join(keywords)
    
    # Initialize an empty list to store URLs
    List_Urls = []
    
    # Step 2: Perform the search and filter based on the desired domains
    allowed_domains = ['bloomberg.com', 'finance.yahoo.com', 'google.com']  # You can modify or add more domains here
    
    for url in search(query, num=10, stop=10, pause=2):
        # Check if the URL contains any of the allowed domains
        if any(domain in url for domain in allowed_domains):
            List_Urls.append(url)
        
        # Stop when we've reached the desired number of URLs
        if len(List_Urls) >= num_urls:
            break
    
    return List_Urls

# Example usage
if __name__ == "__main__":
    user_input = input("Hello! How can I help you? ").strip()
    model_name = "gpt-3.5-turbo"  # Specify the model you want to use
    urls = get_urls(user_input, model_name)
    print(urls)

