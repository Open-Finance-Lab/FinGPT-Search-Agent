Agent Setup
===========

Using pre-built installer scripts
---------------------------------
- Step-by-step guide on how to run/install the Agent locally or via the installer script.
- Any prerequisites, environment variables, etc.

.. note::
   You will need an API key for running the agent. Please ask the project leader (FlyM1ss) via Discord / WeChat / Email (felixflyingt@gmail.com) for the key.

.. note::
   It is genuinely a good practice to run python projects inside a virtual environment. If you are running python 3,
   please replace ``python`` with ``python3`` in the commands below.

Clone Repository
----------------

Clone the repo into an empty directory of your choice. If you don't know how to clone, below is a guide you can
follow. If you do, please skip to *Install the Agent* section.

Recommended Cloning Method: GitHub Desktop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    You may choose to use Git commands to clone the repository. However, they require more technical knowledge than
    Github Desktop. If you are interested or do not want to install Github Desktop, feel free to checkout
    `Github's documentation <https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository?tool=cli>`_
    on cloning repositories using Git.

1. **Download and Install GitHub Desktop**

   - Visit https://desktop.github.com/ to download the latest version for your operating system.
   - Complete the installation.


2. **Open GitHub Desktop and Sign In**

   - Launch GitHub Desktop and sign in with your GitHub account.


3. **Clone the Repository**

   - In GitHub Desktop, click **File** > **Clone repository...**.
   - Select the **URL** tab and paste:
     ``https://github.com/Open-Finance-Lab/FinGPT-Search-Agent``

   - Choose a local path (an empty directory) where you want to store the project files.
   - Click **Clone**.


4. **Switch to the Correct Branch**

   - In GitHub Desktop, confirm that the repository is open.
   - At the top center of the app, there’s a dropdown showing the currently active branch.
   - Change this from ``main`` to ``fingpt_local_singleModel`` by selecting the branch from the dropdown list.
   - If you don’t see the branch listed, click **Fetch** from the top menu. The branch should show up after fetching
     is complete.


5. **Verify**

   - Your GitHub Desktop window should now display the `fingpt_local_singleModel` branch as your active branch.



6. **Prepare your `.env` file**

   - Create (or copy/paste) the file ``.env`` into 
     ``{rootFolderName}\ChatBot-Fin\chat_server\datascraper``.  
   - If creating the file, use an IDE (rather than Notepad) to avoid format issues.
   - Paste the API key into the file and save.

Install the Agent
-----------------

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
