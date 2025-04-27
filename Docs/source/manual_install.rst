Manually Install the Agent
==========================

.. admonition:: When to use this section
   :class: note

   These steps are **only** necessary if the *installer script* has **not** run
   (or failed) (Or if you prefer manual install).
   If you have already run the installer successfully, skip to
   :ref:`start-agent-ready` to verify the extension's installation and how to use
   the agent.

Prerequisites
-------------

* **Python 3.10 +** (or newer) with ``pip``
* **Node.js 18 +** (includes ``npm``) – for building the front-end
* A modern browser that supports Web-Extensions (Chrome, Edge, Brave, Arc …)
* Your **OpenAI API key** saved in the project’s ``.env`` file
  (see *Agent Setup → Installation* for details)

.. _step-0-update:

Update the Repository
---------------------

1. **Open GitHub Desktop**.
2. Make sure the branch dropdown shows either **``fingpt_local_singleModel``**
   or **``main``**.
3. Click **Fetch origin**.
4. If **Pull origin** appears, click it as well.
   When no further action is required, your local copy is up to date.

Create & Activate a Virtual Environment
---------------------------------------

1. Open **Terminal/PowerShell** and *cd* into the **project root**
   (the folder that contains ``backend`` and ``frontend``).

2. **Create the venv** (run **only once**):

   .. code-block:: bash

      python -m venv FinGPTenv

3. **Activate** the venv:

   *macOS / Linux*

   .. code-block:: bash

      source FinGPTenv/bin/activate

   *Windows (PowerShell)*

   .. code-block:: powershell

      .\FinGPTenv\Scripts\Activate.ps1

   When activation succeeds your prompt changes from ``(base)`` (or nothing)
   to ``(FinGPTenv)``.

Install Back-End & Build Front-End
----------------------------------

2.1  Install Python dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # macOS / Linux
   pip install -r Requirements/requirements_mac.txt

   # Windows
   pip install -r Requirements/requirements_win.txt

2.2  Build the front-end bundle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd Main/frontend
   npm install          # installs JS packages (first time only)
   npm run build:full   # creates production bundle

Make sure the build finishes **without errors**.

2.3  Start the back-end server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd ../backend
   python manage.py runserver

A successful start ends with a line such as:
Django version X.Y, using settings 'chat_server.settings' Quit the server with CTRL-BREAK


.. _start-agent-ready:

Load / Reload the Browser Extension
-----------------------------------

1. Open your browser and navigate to **Extensions › Manage Extensions**
   (the puzzle-piece icon in Chrome-based browsers).
2. **Remove** any existing *FinGPT Search Agent* extension.
3. Enable **Developer Mode** (usually a toggle in the upper-right corner).
4. Click **Load Unpacked** (upper-left), navigate to
   ``Main/frontend/dist`` and select the **``dist``** folder.

If the extension loads without error you will see
*FinGPT Search Agent 4.0.0* in the list.

Use the Agent
-------------

* Browse to any *supported* website – the Agent UI should pop up automatically. Check ``manifest.json`` located in ``frontend/src``
  to see the full list of supported sites.
* Start chatting!

Shut Down / Restart
-------------------

* **Close** the browser tab to stop the front-end.
* In the terminal terminate the back-end with ``Ctrl+C`` (``Cmd+C`` on macOS).

.. rubric:: Quick Restart Tip

If you hit a bug, a clean restart often helps:

1. In Terminal, press ``Ctrl+C`` to stop the server.
2. Press the *up-arrow* ``↑`` to recall
   ``python manage.py runserver`` and press **Enter**.

Basic Troubleshooting
~~~~~~~~~~~~~~~~~~~~~

* **Build errors** during ``npm run build:full``
  → Ensure you have Node.js 18+ and reinstall with ``npm ci``.
* **Missing packages** inside the venv
  → Re-run ``pip install -r <requirements_file>.txt``.
* **Extension fails to load**
  → Verify you pointed at ``dist`` (not ``src``) and Developer Mode is ON.
* **Unhandled errors**
  → Contact *FlyM1ss* with the terminal log and browser console output.

