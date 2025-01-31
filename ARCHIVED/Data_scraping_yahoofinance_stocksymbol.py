import requests
from bs4 import BeautifulSoup
import openai 


message_list = [
        {"role": "system", "content": "You are a helpful assistant"}

]
def ai_reponse(user_input):

    client = openai.OpenAI(base_url = "" + "/api/v1", api_key = "api_key_example")



    message = input("Enter question: ")
    message_list.append({"role": "user", "content": message})

    completion = client.chat.completions.create(
        model = "gpt-3.5-turbo",
        messages= message_list
    )

    return (completion.choices[0].message)

def get_stock_info(stock_symbol):
    # Construct the URL for Yahoo Finance
    url = f"https://finance.yahoo.com/quote/{stock_symbol}"

#Send a GET request to the URL
    response = requests.get(url)

#Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')
        print(soup.text)


    else:
        return "Failed to retrieve data. Check your internet connection or try again later."

if __name__ == "__main__":
    #Test the function
    stock_symbol = input("Enter stock: ").upper()
    depth = False 
    depth_s = input("Do you want more in depth information on this based on financial institutions? Enter 'Y' for yes or anything else for no ")
    if (depth_s.lower() == 'y'):
        get_stock_info(stock_symbol)