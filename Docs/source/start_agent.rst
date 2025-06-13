Starting the FinGPT Agent on Mac
=================================

This guide will walk you through starting the FinGPT Search Agent on your Mac computer after installation. This guide is designed for users who may not be familiar with technical operations, so we'll explain each step in detail.

Prerequisites
-------------

Before starting, make sure you have:

- Completed the installation process for FinGPT
- A web browser (Chrome, Firefox, Edge, or Safari - but not Brave)
- Access to the Terminal application on your Mac

Step 1: Open Terminal
---------------------

1. Click on the **Finder** icon in your dock (the blue and white smiley face)
2. In the menu bar at the top, click **Go** → **Applications**
3. Open the **Utilities** folder
4. Double-click on **Terminal** to open it

   .. tip::
      You can also use Spotlight search: Press **Command (⌘) + Space**, type "Terminal", and press Enter

Step 2: Navigate to Your FinGPT Project
----------------------------------------

In Terminal, you need to navigate to where your FinGPT project is located. Type the following command and press Enter:

.. code-block:: bash

   cd /path/to/your/fingpt_agent

.. note::
   Replace ``/path/to/your/fingpt_agent`` with the actual location of your FinGPT folder.
   
   For example, if it's in your GitHub folder inside the Documents folder, you would type:
   
   .. code-block:: bash
   
      cd ~/Documents/GitHub/fingpt_agent

Step 3: Check for the Frontend Build
-------------------------------------

1. Navigate to the frontend directory:

   .. code-block:: bash

      cd Main/frontend

2. Check if the ``dist`` folder exists by typing:

   .. code-block:: bash

      ls

3. Look for a folder named ``dist`` in the list that appears.

   - **If you see** ``dist`` → Skip to Step 5
   - **If you don't see** ``dist`` → Continue to Step 4

Step 4: Build the Frontend (if needed)
---------------------------------------

If the ``dist`` folder is not present, you need to build the frontend:

1. Install the necessary packages:

   .. code-block:: bash

      npm i

   Wait for this to complete (it may take a few minutes).

2. Build the frontend:

   .. code-block:: bash

      npm run build:full

   This will create the ``dist`` folder with all necessary files.

Step 5: Return to the Root Directory
-------------------------------------

Navigate back to the main project folder:

.. code-block:: bash

   cd ../..

You should now be in the root ``fingpt_rcos`` directory.

Step 6: Activate the Python Virtual Environment
------------------------------------------------

1. First, check if you have a virtual environment by typing:

   .. code-block:: bash

      ls

   Look for a folder named ``FinGPTenv``.

2. **If FinGPTenv exists**, activate it:

   .. code-block:: bash

      source FinGPTenv/bin/activate

   You should see ``(FinGPTenv)`` appear at the beginning of your Terminal prompt.

3. **If FinGPTenv doesn't exist**, create it first:

   .. code-block:: bash

      python3 -m venv FinGPTenv
      source FinGPTenv/bin/activate

   Then install the required packages:

   .. code-block:: bash

      pip install -r Requirements/requirements_mac.txt
   
   .. note::
      If Poetry is installed, the installer scripts will automatically 
      export updated requirements files from ``pyproject.toml``.

Step 7: Start the Backend Server
---------------------------------

1. Navigate to the backend directory:

   .. code-block:: bash

      cd Main/backend

2. Start the Django server:

   .. code-block:: bash

      python manage.py runserver

   Or if that doesn't work, try:

   .. code-block:: bash

      python3 manage.py runserver

3. **Success indicator**: You should see output ending with something like:

   .. code-block:: text

      Starting development server at http://127.0.0.1:8000/
      Quit the server with CONTROL-C.

   .. important::
      Keep this Terminal window open! The server needs to keep running for FinGPT to work.

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
   - Click the **Select** button

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
      - Making sure the backend server is still running in Terminal

Troubleshooting
---------------

**Extension doesn't appear after loading:**

- Make sure you selected the ``dist`` folder, not any other folder
- Check that Developer mode is ON
- Try refreshing the Extensions page

**Server won't start:**

- Make sure your virtual environment is activated (you should see ``(FinGPTenv)``)
- Try ``python3`` instead of ``python``
- Check that you're in the ``Main/backend`` directory

**Agent popup doesn't appear on websites:**

- Verify the backend server is running (check your Terminal)
- Refresh the webpage
- Check that the extension is enabled in your browser

Stopping the Agent
------------------

When you're done using FinGPT:

1. In the Terminal window running the server, press **Control + C**
2. Type ``deactivate`` to exit the virtual environment
3. You can close the Terminal window

Next Steps
----------

Now that FinGPT is running, you can:

- Ask financial questions using the search agent
- Configure your preferred URLs in the settings
- Explore the different query modes (Basic Ask vs Advanced Ask)

For more information on using FinGPT's features, see :doc:`usage/basic_usage`.