# FinGPT Search Agents

Vision: An agent in finance, business, accounting domains to assist users in information retrieval and data analysis. When generating responses, it provides the information sources to help users evaluate the responses' quality.
 
This is a demo of FinLLMs on the HuggingFace's [Open Financial LLM Leaderboard](https://huggingface.co/spaces/TheFinAI/Open-Financial-LLM-Leaderboard).

1. A powerful information search-and-retrieval engine: A search agent for websites (Math Cup, Yahoo Finance, Bloomberg, XBRL International) and local files (SEC 10K, XBRL files (eXtensible Business Reporting Language)).
2. A powerful answer engine: an answer agent performs open search to quickly locate relevant financial information from various sources, such as websites, reports, filings, and databases
3. For generated responses, users can check the sources, ensuring reliability and accuracy.

**NO Trading Suggestions!**

Current Progress:

1. Snapshot of the search agent: drag, resize and minimize; Providing information on user's current page.
   ![image](https://github.com/YangletLiu/FinLLM-Search-Agent/blob/main/figures/snapshot.png)

2. Checking sources, which are very important and help reduce misinformation.
   ![image](https://github.com/YangletLiu/FinGPT-Search-Agent/blob/main/figures/sources.png)

3. Dedicated RAG for local files (SEC 10K, XBRL files) (Currently requires additional setup to use).


## Installation:
**You will need an API key for running the agent. Please ask the project leader (FlyM1ss) for the key. **
1. Create or copy paste the file ".env" into {rootFolderName}\ChatBot-Fin\chat_server\datascraper. If creating the file,
do it with an IDE (do not edit it with a text editor like Notepad), paste the API key into the file and save.
2. Clone the repo into an empty directory.
3. For Windows, in the root folder, find "Installer_Win.ps1", right click it, and choose "Run with PowerShell". If no 
permission, first navigate into the root folder of this project in File Explorer and left click the address bar to
select the address. Press Ctrl+C to copy. Then, manually open Terminal in Admin mode by right-clicking the task bar and
choose Terminal (Admin). Type "cd" followed by a space and a quotation mark. Then, paste the address and type the second 
quotation mark, and press Enter. Finally, copy "powershell.exe -ExecutionPolicy Bypass -File .\Installer_Win.ps1" into
Terminal and press Enter to run the script. This bypasses the execution policy *only for this execution* to run the
script.
4. For MacOS, in the root folder, find "Installer_Mac.sh", right click it, and choose Open with Terminal.
5. The installer automatically installs the Extension in Google Chrome and starts the back-end. If the extension isn't
installed in Chrome, or you want to have it installed in another browser, go to your desired browser and find Plugins or
Extensions (usually located at top right portion). Enable Developer Mode.
6. Click "Load Unpacked" located the top left corner of Plugins or Extensions page. Navigate to the folder
"{rootFolderName}/ChatBot-Fin/Extension-ChatBot-Fin/src", select and load it.
7. If the back-end isn't automatically started, go to a terminal of your choice and navigate to
"{rootFolderName}\ChatBot-Fin\chat_server"
8. Run the command "python manage.py runserver"  or "python3 manage.py runserver" if using Python3. Wait for the server
to start. This should take no longer than a dozen second (may take a bit longer for the first time).
9. Navigate to a supported website. The search agent should automatically load and scrape the homepage.
10. Start chatting!

Immediate Next Steps:
1. Display Chain of Thought in the context window if applicable.
2. Integrate Deepseek.
3. Try to make the agent render LaTex.
4. Implement a local dynamic database and pre-fetch context (specific websites, news, textbooks, etc.) into it.
5. Users cannot re-open the agent once it is closed. Need to fix it.


Future Plans:
1. Fix context window. Need to add logic handling the context window for Ask and Advanced Ask.
2. Make user-specified web lists more "intelligent", if there is any way for the agent to auto-navigate some websites.
3. Start to promote the demo more and collect questions from users.

Citing:

''''
@inproceedings{tian2024customized,
  title={Customized fingpt search agents using foundation models},
  author={Tian, Felix and Byadgi, Ajay and Kim, Daniel S and Zha, Daochen and White, Matt and Xiao, Kairong and Liu, Xiao-Yang},
  booktitle={Proceedings of the 5th ACM International Conference on AI in Finance},
  pages={469--477},
  year={2024}
}
}
''''


**Disclaimer: We are sharing codes for academic purposes under the MIT education license. Nothing herein is financial 
advice, and NOT a recommendation to trade real money. Please use common sense and always first consult a professional
before trading or investing.**
