# FinGPT-Search-Agent


Vision: A search agent specialized in financce, business, accounting domains to assist users in information retrieval; providing the information sources to help users evaluate the quality of generated responses.


1. A search agent for websites (Yahoo Finance, Bloomberg, XBRL International) and local files (SEC 10K, XBRL files (eXtensible Business Reporting Language)).
2. A powerful information search-and-retrieval engine to quickly locate relevant financial information from various sources, such as websites, reports, filings, and databases.
3. For generated responses, users can check the sources, ensuring reliability and accuracy.
4. This is a demo of FinLLMs on the HuggingFace's [Open Financial LLM Leaderboard](https://huggingface.co/spaces/TheFinAI/Open-Financial-LLM-Leaderboard).


**NO Trading Suggestions!**


Current Progress:


1. Snapshot of the search agent: drag, resize and minimize; Providing information on user's current page.
  ![image](https://github.com/YangletLiu/FinLLM-Search-Agent/blob/main/figures/snapshot.png)


2. Checking sources, which are very important and help reduce misinformation.
  ![image](https://github.com/YangletLiu/FinGPT-Search-Agent/blob/main/figures/sources.png)


3. User's webpage list. A list of URLs (and APIs in the future) that users set higher priority to retrieve information.
  ![image](https://github.com/YangletLiu/FinGPT-Search-Agent/blob/main/figures/user_preferred.png)




## Installation Guide:
**Important**: You will need an API key for running the agent. Please ask the project leader for the key.
1. Open a terminal and navigate to the directory where you want to set up the project.
2. Clone the repository by running the following command: "git clone https://github.com/FlyM1ss/FinGPT_for_RCOS.git"


2. Install the necessary dependencies as shown in the requirements.txt file in the root path via "pip install -r requirements.txt"
3. Go to extensions on a Chrome-Based browser and select developer mode
4. Click "Load unpacked" on the top left corner. Navigate to the folder "FinGPT_For_RCOS/ChatBot-Fin/Extension-ChatBot-Fin/src", select and load it.
5. Go to https://huggingface.co/google/gemma-2-2b-it/tree/main, then follow these steps:
  - Go to the more options botton (button w/ the 3 dots) and click "Clone repository". It will run you through how to  clone the repository:
     - Make sure you have git-lfs installed (https://git-lfs.com): Run "git lfs install"
     - When prompted for a password, use an access token with write permissions. Generate one from your settings: https://huggingface.co/settings/tokens
     - Now go to your terminal and navigate to "FinGPT_For_RCOS/ChatBot-Fin/chat_server/datascraper" and run "git clone https://huggingface.co/google/gemma-2-2b-it"
     - (Optional) If you want to clone without large files - just their pointers: "GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/google/gemma-2-2b-it"
     - Now that we have done that, we should now have "gemma-2-2b-it" in our "FinGPT_For_RCOS/ChatBot-Fin/chat_server/datascraper"
6. Now create a new terminal, then go to FinGPT_For_RCOS/ChatBot-Fin and run the command "python manage.py runserver" or "python3 manage.py runserver" if using Python3. Wait for the server to start. This should take no longer than a couple seconds.
7. Navigate to https://finance.yahoo.com/ or https://www.bloomberg.com/. The search agent should automatically load and scrape the homepage.
8. Start chatting!


Immediate Next Steps:
1. Design a RAG specific for CDM (rule and program pairing, controlled generation)
2. Local file parsing
3. Make the installation easier.
4. Users cannot re-open the agent once it is closed. Need to fix it.




Future Plans:
1. Reduce response time and sources loading by improving datascraping.py.
2. Build a dynamic database for users: personalized version.
3. Fix context window. Need to add logic handling the context window for Ask and Advanced Ask.
4. Make user-specified web lists more "intelligent", if there is any way for the agent to auto-navigate some websites.
5. Start to promote the demo more and collect questions from users.
6. Test different FinLLMs models like LLaMA3, on the HuggingFace's [Open Financial LLM Leaderboard](https://huggingface.co/spaces/TheFinAI/Open-Financial-LLM-Leaderboard).




**Disclaimer: We are sharing codes for academic purposes under the MIT education license. Nothing herein is financial advice, and NOT a recommendation to trade real money. Please use common sense and always first consult a professional before trading or investing.**


