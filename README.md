# FinGPT Agents

Vision: An agent in finance, business, accounting domains to assist users in information retrieval and data analysis. When generating responses, it provides the information sources to help users evaluate the responses' quality.
 
This is a demo of FinLLMs on the HuggingFace's [Open Financial LLM Leaderboard](https://huggingface.co/spaces/TheFinAI/Open-Financial-LLM-Leaderboard).

1. A powerful information search-and-retrieval engine: A search agent for websites (Math Cup, Yahoo Finance, Bloomberg, XBRL International) and local files (SEC 10K, XBRL files (eXtensible Business Reporting Language)).
2. A powerful answer engine: an answer agent performs open search to quickly locate relevant financial information from various sources, such as websites, reports, filings, and databases
3. For generated responses, users can check the sources, ensuring reliability and accuracy.

**NO Trading Suggestions!**

Current Progress:

1. Snapshot of the search agent: drag, resize and minimize; Providing information on user's current page.
   ![image](https://github.com/Open-Finance-Lab/FinGPT-Search-Agent/tree/fingpt_local_singleModel/figures/F4.0_1.png)

2. Checking sources, which are very important and help reduce misinformation.
   ![image](https://github.com/Open-Finance-Lab/FinGPT-Search-Agent/tree/fingpt_local_singleModel/figures/F4.0_Source.png)

3. Dedicated RAG for local files (SEC 10K, XBRL files).
   ![image](https://github.com/Open-Finance-Lab/FinGPT-Search-Agent/tree/fingpt_local_singleModel/figures/F4.0_RAG_1.png)


## Installation, Usage, and more
Reference the [documentation](https://fingpt-search-agent-docs.readthedocs.io/en/latest/)!


Immediate Next Steps:
1. Integrate MCP servers for a proof-of-concept.
2. Integrate Deepseek.
3. Try to make the agent render LaTex.

Future Plans:
1. zkp demo.


**Disclaimer: We are sharing codes for academic purposes under the MIT education license. Nothing herein is financial 
advice, and NOT a recommendation to trade real money. Please use common sense and always first consult a professional
before trading or investing.**
