Starting the FinGPT Agent on Windows
====================================

This guide will walk you through starting the FinGPT Search Agent on your Windows computer after installation. This guide is designed for users who may not be familiar with technical operations, so we'll explain each step in detail.

.. note::
   You can always automatically start the search agent with the provided scripts:

   1. Open your Command Prompt or PowerShell and cd into the project's root directory (where you cloned the repository)

   2. Run either of the following::

       # Using PowerShell
       .\make.ps1 dev
      
       # Or directly
       python scripts/dev_setup.py

   This will start the back-end server and build the front-end bundle. You may now continue from :ref:`Step 8: Load the Extension in Your Browser <step-8-load-extension-win>`.

Prerequisites
-------------

Before starting, make sure you have:

- Completed the installation process for FinGPT
- A web browser (Chrome, Firefox, or Edge - but not Brave)
- Access to Command Prompt or PowerShell on your Windows computer

Step 1: Open Command Prompt or PowerShell
-----------------------------------------

You can use either Command Prompt or PowerShell. We'll show you how to open both:

**Option A: Command Prompt**

1. Press the **Windows key** on your keyboard (or click the Windows icon in the taskbar)
2. Type "cmd" (without quotes)
3. Click on **Command Prompt** when it appears in the search results

**Option B: PowerShell (Recommended)**

1. Press the **Windows key** on your keyboard
2. Type "powershell" (without quotes)  
3. Click on **Windows PowerShell** when it appears in the search results

   .. tip::
      You can also right-click the Windows Start button and select **Windows PowerShell**

Step 2: Navigate to Your FinGPT Project
----------------------------------------

In your Command Prompt or PowerShell window, you need to navigate to where your FinGPT project is located.

.. code-block:: powershell

   cd C:\path\to\your\fingpt_search_agent

.. note::
   Replace ``C:\path\to\your\fingpt_search_agent`` with the actual location of your FinGPT folder.
   
   For example, if it's in your GitHub folder inside the Documents folder, you would type:
   
   .. code-block:: powershell
   
      cd C:\Users\YourName\Documents\GitHub\fingpt_agent

   Replace ``YourName`` with your actual Windows username.

Step 3: Check for the Frontend Build
-------------------------------------

1. Navigate to the frontend directory:

   .. code-block:: powershell

      cd Main\frontend

2. Check if the ``dist`` folder exists by typing:

   .. code-block:: powershell

      dir

3. Look for a folder named ``dist`` in the list that appears.

   - **If you see** ``dist`` → Skip to Step 5
   - **If you don't see** ``dist`` → Continue to Step 4

Step 4: Build the Frontend (if needed)
---------------------------------------

If the ``dist`` folder is not present, you need to build the frontend. In your Command Prompt or PowerShell, while in Main\frontend, run the following commands:

1. Install the necessary packages:

   .. code-block:: powershell

      npm i

   Wait for this to complete (it should take at most a few minutes).

2. Build the frontend:

   .. code-block:: powershell

      npm run build:full

   This will create the ``dist`` folder with all necessary files.

Step 5: Return to the Root Directory
-------------------------------------

Navigate back to the main project folder:

.. code-block:: powershell

   cd ..\..

You should now be in the root directory.

Step 6: Activate the Python Virtual Environment
------------------------------------------------

1. First, check if you have a virtual environment by typing:

   .. code-block:: powershell

      dir

   Look for a folder named ``FinGPTenv``.

2. **If FinGPTenv exists**, activate it:

   .. code-block:: powershell

      FinGPTenv\Scripts\activate

   You should see ``(FinGPTenv)`` appear at the beginning of your command prompt.

3. **If FinGPTenv doesn't exist**, create it first:

   .. code-block:: powershell

      python -m venv FinGPTenv
      FinGPTenv\Scripts\activate

   Then install the required packages:

   .. code-block:: powershell

      pip install -r Requirements\requirements_win.txt
   
   .. note::
      If Poetry is installed, the installer scripts will automatically 
      export updated requirements files from ``pyproject.toml``.

Step 7: Start the Backend Server
---------------------------------

1. Navigate to the backend directory:

   .. code-block:: powershell

      cd Main\backend

2. Start the Django server:

   .. code-block:: powershell

      python manage.py runserver

3. **Success indicator**: You should see output ending with something like:

   .. code-block:: text

      Starting development server at http://127.0.0.1:8000/
      Quit the server with CTRL-BREAK.

   .. important::
      Keep this Command Prompt or PowerShell window open! The server needs to keep running for FinGPT to work.

.. _step-8-load-extension-win:

Step 8: Load the Extension in Your Browser
-------------------------------------------

Now let's set up the FinGPT extension in your browser. We'll use Chrome as an example, but the process is similar for other browsers.

**For Google Chrome:**

1. Open Chrome
2. Click the three dots menu (⋮) in the top-right corner
3. Go to **More tools** → **Extensions**

   .. tip::
      You can also type ``chrome://extensions`` in the address bar and press Enter

4. Look for **FinGPT Search Agent** in your extensions list
   
   - **If you see it** → Make sure the toggle switch is ON (blue)
   - **If you don't see it** → Continue to load it manually:

**To Load the Extension Manually:**

1. In the Extensions page, toggle **Developer mode** ON (top-right corner)
   
   .. note::
      Developer mode switch is usually in the top-right corner of the Extensions page

2. Click the **Load unpacked** button that appears
3. In the file browser that opens:
   
   - Navigate to your FinGPT project folder
   - Open **Main** → **frontend**
   - Click once on the **dist** folder to select it (it should be highlighted)
   - Click the **Select Folder** button

4. FinGPT Search Agent should now appear in your extensions list

Step 9: Test the Agent
----------------------

1. Navigate to a supported financial website like:
   
   - https://finance.yahoo.com
   - https://www.bloomberg.com
   - Any page with financial content

2. The FinGPT Search Agent popup should automatically appear!

   .. tip::
      If the popup doesn't appear, try:
      
      - Refreshing the page
      - Clicking the FinGPT extension icon in your browser toolbar
      - Making sure the backend server is still running in your Command Prompt or PowerShell

Troubleshooting
---------------

**Extension doesn't appear after loading:**

- Make sure you selected the ``dist`` folder, not any other folder
- Check that Developer mode is ON
- Try refreshing the Extensions page

**Server won't start:**

- Make sure your virtual environment is activated (you should see ``(FinGPTenv)``)
- Try running the command prompt or PowerShell as Administrator
- Check that you're in the ``Main\backend`` directory

**Agent popup doesn't appear on websites:**

- Verify the backend server is running (check your Command Prompt or PowerShell)
- Refresh the webpage
- Check that the extension is enabled in your browser
- Check that you're on a supported browser and supported website

**Permission errors:**

- Try running Command Prompt or PowerShell as Administrator (right-click → Run as administrator)
- Make sure Windows Defender or antivirus isn't blocking the application

Stopping the Agent
------------------

When you're done using FinGPT:

1. In the Command Prompt or PowerShell window running the server, press **Ctrl + C**
2. Type ``deactivate`` to exit the virtual environment
3. You can close the Command Prompt or PowerShell window

Next Steps
----------

Now that FinGPT is running, you can:

- Ask financial questions using the search agent
- Configure your preferred URLs in the settings
- Explore the different query modes (Basic Ask vs Advanced Ask)

For more information on using FinGPT's features, see :doc:`usage/basic_usage`.