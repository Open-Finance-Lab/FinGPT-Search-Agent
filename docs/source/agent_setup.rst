Agent Setup
===========

Using pre-built installer scripts
---------------------------------
- Step-by-step guide on how to run/install the Agent locally or via the installer script.
- Any prerequisites, environment variables, etc.

Installation
------------

.. note::
   You will need an API key for running the agent. Please ask the project leader (FlyM1ss) via Discord / WeChat / Email (felixflyingt@gmail.com) for the key.

.. note::
   It is genuinely a good practice to run python projects inside a virtual environment. If you are running python 3,
   please replace ``python`` with ``python3`` in the commands below.

Clone the repository
~~~~~~~~~~~~~~~~~~~~

   - Clone the repo into an empty directory of your choice. If you don't know how to clone, below is a guide that you may follow:



   **Prepare your `.env` file**:

   - Create (or copy/paste) the file ``.env`` into 
     ``{rootFolderName}\ChatBot-Fin\chat_server\datascraper``.  
   - If creating the file, use an IDE (rather than Notepad) to avoid format issues.
   - Paste the API key into the file and save.


Windows
~~~~~~~

1. In the project’s **root folder**, locate the file ``Installer_Win.ps1``.
2. **Right-click** it and select **"Run with PowerShell"**. 
   
   - If you face permission issues, do the following:
     
     - Navigate to the project’s root folder in File Explorer.
     - Click the address bar to select the path, then press **Ctrl+C** to copy.
     - Open a **Terminal** (Admin mode).  
       - Right-click the task bar and select **Terminal (Admin)**
       - Type ``cd "``, paste the path you copied, then type ``"`` and press Enter.
     - Finally, run
       ::

         powershell.exe -ExecutionPolicy Bypass -File .\Installer_Win.ps1

     - This bypasses the execution policy **only** for this script run.
3. The installer attempts to:
   - Install the Extension in Google Chrome
   - Start the back-end
4. If the Extension is **not** automatically installed, or you want to use another browser:
   
   - Enable Developer Mode in that browser’s Extensions/Plugins panel.
   - Click **"Load Unpacked"** and navigate to  
     ``{rootFolderName}/ChatBot-Fin/Extension-ChatBot-Fin/src``  
     to select and load the extension manually.
5. If the **back-end** isn’t started automatically:
   - Open a terminal and navigate to  
   ``{rootFolderName}\ChatBot-Fin\chat_server``

   - Run:
     ::

       python manage.py runserver
   - Wait a few seconds for the server to start.

Mac
~~~

1. In the project’s **root folder**, locate the file ``Installer_Mac.sh``.
2. Right-click it and select **"Open with Terminal"**.
3. The installer attempts to:
   - Install the Extension in Google Chrome
   - Start the back-end
4. If the Extension is **not** automatically installed, or you want to use another browser:
   - Enable Developer Mode in that browser’s Extensions/Plugins panel.
   - Click **"Load Unpacked"** and navigate to  
   ``{rootFolderName}/ChatBot-Fin/Extension-ChatBot-Fin/src`` to select and load the extension manually.

5. If the **back-end** isn’t automatically started:
   - Open a terminal and navigate to  
   ``{rootFolderName}\ChatBot-Fin\chat_server``

   - Run:
     ::

       python manage.py runserver
   - Wait for the server to initialize.

Final Steps
-----------

- Navigate to any supported website (Math Cup, Yahoo Finance, Bloomberg, XBRL International).  
- The search agent should automatically load and scrape the homepage.  
- **Start chatting!**
