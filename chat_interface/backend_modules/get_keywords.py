import os
from dotenv import load_dotenv
import openai
import requests

"""
Takes user input which can be a fairly long string, and returns
a list of a few(1 to 5) of the key words(strings) found in the string in order
to help with search querying
"""


def get_keywords(user_input: str, model_name: str) -> list:
    # Get the API key to use OpenAI models
    load_dotenv(dotenv_path='ChatBot-Fin/chat_server/datascraper/.env')
    openai.api_key = os.getenv("API_KEY7")

    # Using the specified model (either GPT-4o or GPT-3.5-turbo)
    completion = openai.ChatCompletion.create(
        model=model_name,  # Use the model passed as an argument
        messages=[{"role": "system", "content": "You return all the keywords from this request separated by a comma only?:\n" + user_input}],
    )

    print(f"{model_name} response: ", completion.choices[0].message.content)
    keywords = completion.choices[0].message.content.split(",")
    print(keywords)
    return keywords

# multiple models
def get_keywords_from_models(user_input: str, models: list) -> dict:
    results = {}
    for model in models:
        results[model] = get_keywords(user_input, model)
    return results


# def get_keywords(user_input: str) -> list:
#     # Get the API key to use GPT 3.5 (Remove if not needed)
#     # load_dotenv()
#     # openai.api_key = os.getenv("API_KEY7")
#
#     # Using LLaMA 3.1, find the keywords of the user's request
#     response = query_llama("You return all the keywords from this request separated by a comma only?:\n" + user_input)
#     print(response)
#     keyWords = response.split(",")
#     print(keyWords)
#     return keyWords
#
#
# def query_llama(question: str) -> str:
#     url = "http://localhost:11434/api/generate"  # Adjust the URL to match your LLaMA 3.1 endpoint
#     payload = {
#         "model": "llama3.1",  # Adjust the model name if needed
#         "prompt": question,
#         "stream": False
#     }
#     headers = {"Content-Type": "application/json"}
#
#     response = requests.post(url, json=payload, headers=headers)
#     response.raise_for_status()
#     return response.json()['choices'][0]['message']['content']


if __name__ == "__main__":
    user = input("Hello! How can I help you? ").strip()
    model_name = "gpt-3.5-turbo"  # or "gpt-4", depending on the model you want to use
    get_keywords(user, model_name)

