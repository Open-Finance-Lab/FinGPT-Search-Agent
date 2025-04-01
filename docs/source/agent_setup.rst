Agent Setup
===========

- Step-by-step guide on how to run/install the Agent via the installer script. The scripts automatically installs
  the agent to **Google Chrome** by default. If you want to install to a different browser, please see **Step 4** of
  the section **Windows** - ``Install the Agent``.
- Any prerequisites, environment variables, etc.

.. note::
   You will need an OpenAI API key for running the agent. Please ask the project leader (FlyM1ss) via Discord /
   WeChat / Email (felixflyingt@gmail.com) for the key. If you have your own key, feel free to create a ``.env`` file
   inside ``{rootFolderName}\ChatBot-Fin\chat_server\datascraper`` and put in the form of ``API_KEY7=Your-Key``.

.. note::
   If you are running python 3 and the commands below don't work, please replace any ``python`` within the command to
    ``python3``.

Clone Repository
----------------

Clone the repo into an empty directory of your choice. If you don't know how to clone, below is a guide you can
follow. If you do, please skip to *Install the Agent* section.

Recommended Cloning Method: GitHub Desktop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

1. **Find Corresponding Installer Scripts**

  Open File Explorer and navigate to the project’s **root folder** (by default it should be called
  "FinGPT-Search-Agent"). Locate the file ``Installer_Win.ps1``.

2. **Execute Installer Script**

  **Right-click** the installer script and select **"Run with PowerShell"**.
   
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

  The installer will attempt to:

    - Install the Extension in Google Chrome
    - Create and start a Python virtual environment.
    - Start the back-end

3. **Check Front-end Installation**

  Open Google Chrome, navigate to any supported websites and see if the agent pops up. If **nothing is showing**, or you
  want to **use another browser**:

    - Find and open the Extension Page. It's usually opened by clicking a "puzzle piece" button or under ``Settings``.
    - Find and enable Developer Mode in that browser’s Extensions/Plugins panel.
    - Click **"Load Unpacked"** and navigate to ``{rootFolderName}/ChatBot-Fin/Extension-ChatBot-Fin``, click ``src``
      to select the folder, and hit Enter or click **Select Folder**.
    - Make sure you see "FinGPT" inside the Extension/Plugin page.

4. **Check Back-end Installation**

  A successful start of the back-end should create a separate terminal window and have something like **Quit the server
  with CTRL-BREAK** displayed at the last line. If the back-end isn’t started automatically or the starting failed:

    - Open a terminal and navigate to
      ``{rootFolderName}\ChatBot-Fin\chat_server``

    - Run:
      ::

        python manage.py runserver

    - Wait a few seconds for the server to start.

  If issues persists, they are most likely issues one without technical abilities won't be able to solve. You may ask
  AI chatbots to help you debug and start the agent, or kindly request those possessing the holy power of programming
  to assist with the dire situation.

Mac
~~~

1. **Find Corresponding Installer Scripts**

  Open Finder and navigate to the project’s **root folder** (by default it should be called "FinGPT-Search-Agent").
  Locate the file ``Installer_Mac.sh``.

2. **Execute Installer Script**

  Right-click it and select **"Open with Terminal"**. If you can't see such options:

    - Manually open Terminal.
    - ``cd`` into this project's **root folder**. If you don't know how to do this, refer to `this tutorial <https://www.youtube.com/watch?v=VRFcEMPES7U>`_.
    - Give the script execute permission by typing ``chmod +x script.sh`` and hit Enter.
    - Type ``./Installer_Mac.sh`` to run the script.

  The installer will attempt to:

    - Install the Extension in Google Chrome
    - Create and start a Python virtual environment.
    - Start the back-end

3. **Check Front-end Installation**

  If the Extension is **not** automatically installed, or you want to use another browser:

    - Enable Developer Mode in that browser’s Extensions/Plugins panel.
    - Click **"Load Unpacked"** and navigate to
      ``{rootFolderName}/ChatBot-Fin/Extension-ChatBot-Fin/src`` to select and load the extension manually.

4. **Check Back-end Installation**

  A successful start of the back-end should create a separate terminal window and have something like **Quit the server
  with CTRL-BREAK** displayed at the last line. If the back-end isn’t started automatically or the starting failed:

    - Open a terminal and navigate to
      ``{rootFolderName}\ChatBot-Fin\chat_server``

    - Run:
      ::

        python manage.py runserver

    - Wait a few seconds for the server to start.

Final Steps
-----------

- Navigate to any supported website.
- The search agent should automatically load and scrape the homepage.  
- **Start chatting!**
