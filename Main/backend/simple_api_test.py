from openai import OpenAI

# Initialize client pointing to local FinGPT instance
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sk-dummy-key"
)

def test_chat():
    print("Sending request to FinGPT...")
    
    # 1. Standard Chat Completion with Mode and URL
    # Using example.com for reliable scraping test
    print("\n--- Test 1: Thinking Mode with URL (example.com) ---")
    completion = client.chat.completions.create(
        model="FinGPT",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Analyze the content of the page I provided. What is the domain?"}
        ],
        extra_body={
            "mode": "thinking",
            "url": "https://finance.yahoo.com/"
        }
    )
    print(f"Response: {completion.choices[0].message.content}")

    # 2. Research Mode Example
    print("\n\n--- Test 2: Research Mode (Web Search) ---")
    completion = client.chat.completions.create(
        model="FinGPT",
        messages=[{"role": "user", "content": "How is the world of crypto going?"}],
        extra_body={
            "mode": "research" # Triggers web search
        }
    )
    print(f"Response: {completion.choices[0].message.content}")


if __name__ == "__main__":
    test_chat()
