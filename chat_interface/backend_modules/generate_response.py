'''
Use GPT-3.5 API to generate response from the user input. We will be 
using "Retrieval Augmented Generation" to add the context of the scraping 
the "get_urls" and "clean_urls" modules will return.

Input will be a string(user input) and a list of maps(data) of the form {URL:text}.
The output should be a string.
'''
def generate_response(user_input:str, data:list) -> str:
    pass