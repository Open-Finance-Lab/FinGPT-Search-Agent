# FinGPT-Search-Agent


Vision: A search agent specialized in finance, business, accounting domains to assist users in information retrieval and analysis. 

1. A search agent for financial websites (Yahoo Finance, Bloomberg, XBRL International) and local files (SEC 10K, XBRL files (eXtensible Business Reporting Language)).
2. A powerful information engine to quickly locate relevant financial information from various sources, such as websites, reports, filings, and databases.
3. For generated responses, users can double-check the information sources for generated responses.
4. This project provide a demo for FinLLMs at the HuggingFace's [Open Financial LLM Leaderboard](https://huggingface.co/spaces/TheFinAI/Open-Financial-LLM-Leaderboard).


**NO Trading Suggestions!**


Progress:


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


3. Install the necessary dependencies as shown in the requirements.txt file in the root path via "pip install -r requirements.txt"
4. Go to extensions on a Chrome-Based browser and select developer mode
5. Click "Load unpacked" on the top left corner. Navigate to the folder "FinGPT_For_RCOS/ChatBot-Fin/Extension-ChatBot-Fin/src", select and load it.


[//]: # (5. Go to https://huggingface.co/google/gemma-2-2b-it/tree/main, then follow these steps:)

[//]: # (  - Go to the more options botton &#40;button w/ the 3 dots&#41; and click "Clone repository". It will run you through how to  clone the repository:)

[//]: # (     - Make sure you have git-lfs installed &#40;https://git-lfs.com&#41;: Run "git lfs install")

[//]: # (     - When prompted for a password, use an access token with write permissions. Generate one from your settings: https://huggingface.co/settings/tokens)

[//]: # (     - Now go to your terminal and navigate to "FinGPT_For_RCOS/ChatBot-Fin/chat_server/datascraper" and run "git clone https://huggingface.co/google/gemma-2-2b-it")

[//]: # (     - &#40;Optional&#41; If you want to clone without large files - just their pointers: "GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/google/gemma-2-2b-it")

[//]: # (     - Now that we have done that, we should now have "gemma-2-2b-it" in our "FinGPT_For_RCOS/ChatBot-Fin/chat_server/datascraper")



6. Now create a new terminal, then go to FinGPT_For_RCOS/ChatBot-Fin and run the command "python manage.py runserver" or "python3 manage.py runserver" if using Python3. Wait for the server to start. This should take no longer than a couple seconds.
7. Navigate to https://finance.yahoo.com/ or https://www.bloomberg.com/. The search agent should automatically load and scrape the homepage.
8. Start chatting!

**NOTE:** There is an option under Settings window for enabling local RAG. It is a function under development and additional steps are required to get it working. 
If you want to try it out, please contact Felix Tian (FlyM1ss) on discord. 
I will update the README once it is ready.

Immediate Next Steps:
1. Local file parsing's document
2. SEC Filing's parsing (should be very similar to CDM files parsing)
3. Make the installation easier.
4. Users cannot re-open the agent once it is closed. Need to fix it.



Future Plans:
1. Reduce response time and sources loading by improving datascraping.py.
2. Build a dynamic database for users: personalized version.
3. Fix context window. Need to add logic handling the context window for Ask and Advanced Ask.
4. Make user-specified web lists more "intelligent", if there is any way for the agent to auto-navigate some websites.
5. Start to promote the demo more and collect questions from users.
6. Test different FinLLMs models like LLaMA3, on the HuggingFace's [Open Financial LLM Leaderboard](https://huggingface.co/spaces/TheFinAI/Open-Financial-LLM-Leaderboard).


Citation

''
@inproceedings{tian2024customized,
  title={Customized FinGPT Search Agents Using Foundation Models},
  author={Tian, Felix and Byadgi, Ajay and Kim, Daniel S and Zha, Daochen and White, Matt and Xiao, Kairong and Liu, Xiao-Yang},
  booktitle={Proceedings of the 5th ACM International Conference on AI in Finance},
  pages={469--477},
  year={2024}
}
''


**Disclaimer: We are sharing codes for academic purposes under the MIT education license. Nothing herein is financial advice, and NOT a recommendation to trade real money. Please use common sense and always first consult a professional before trading or investing.**


