'''
takes as input an array of key words, combines them into a single string,
and then searches the web to find 1-5 urls that match the most with
the keywords provided.

The URLs should be returned as a list of strings.

The main websites we will be searching for now will be bloomberg, yahoo finance, and 
google search. If you want, you can use other sites in your implementation
'''

from googlesearch import search

def get_urls(query) -> list:
    List_Urls = []
    for url in search(query, num=10, stop=10, pause =0):
        List_Urls.append(url)

