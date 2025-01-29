# FinGPT-Search-Agent

Vision: A search agent specialized in finance, business, accounting domains to assist users in information retrieval; providing the information sources to help users evaluate the quality of generated responses.

1. A search agent for websites (Math Cup, Yahoo Finance, Bloomberg, XBRL International) and local files (SEC 10K, XBRL files (eXtensible Business Reporting Language)).
2. A powerful information search-and-retrieval engine to quickly locate relevant financial information from various sources, such as websites, reports, filings, and databases.
3. For generated responses, users can check the sources, ensuring reliability and accuracy.
4. This is a demo of FinLLMs on the HuggingFace's [Open Financial LLM Leaderboard](https://huggingface.co/spaces/TheFinAI/Open-Financial-LLM-Leaderboard).

**NO Trading Suggestions!**

Current Progress:

1. Snapshot of the search agent: drag, resize and minimize; Providing information on user's current page.
   ![image](https://github.com/YangletLiu/FinLLM-Search-Agent/blob/main/figures/snapshot.png)

2. Checking sources, which are very important and help reduce misinformation.
   ![image](https://github.com/YangletLiu/FinGPT-Search-Agent/blob/main/figures/sources.png)

3. Dedicated RAG for local files (SEC 10K, XBRL files) (Currently requires additional setup to use).


## Installation:
**You will need an API key for running the agent. Please ask the project leader （FlyM1ss) for the key.**
1. Clone the repo into an empty directory.
2. In the root folder, find "installDepdencies.sh" and double click it to install packages necessary for local deployment.
3. Create the file ".env" at {rootFolderName}\ChatBot-Fin\chat_server\datascraper. With an IDE (do not edit it with a text editor like Notepad), paste the API key into the file and save.
4. Now, go to your desired browser and find Plugins or Extensions (usually located at top right portion). Enable Developer Mode.
5. Click "Load Unpacked" located the top left corner of Plugins or Extensions page. Navigate to the folder "{rootFolderName}/ChatBot-Fin/Extension-ChatBot-Fin/src", select and load it.
6. Go to a terminal of your choice and navigate to "{rootFolderName}\ChatBot-Fin\chat_server"
7. Run the command "python manage.py runserver"  or "python3 manage.py runserver" if using Python3. Wait for the server to start. This should take no longer than a couple seconds.
8. Navigate to "https://finance.yahoo.com/" or "https://www.bloomberg.com/". The search agent should automatically load and scrape the homepage.
9. Start chatting!

Immediate Next Steps:
1. Integrate into Math Cup and related projects (AI Tutor for Math Cup).
2. Implement a local dynamic database and pre-fetch context (specific websites, news, textbooks, etc.) into it.
3. Users cannot re-open the agent once it is closed. Need to fix it.


Future Plans:
1. Fix context window. Need to add logic handling the context window for Ask and Advanced Ask.
2. Make user-specified web lists more "intelligent", if there is any way for the agent to auto-navigate some websites.
3. Start to promote the demo more and collect questions from users.


**Disclaimer: We are sharing codes for academic purposes under the MIT education license. Nothing herein is financial advice, and NOT a recommendation to trade real money. Please use common sense and always first consult a professional before trading or investing.**
