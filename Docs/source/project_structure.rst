File Structure
======================

This project currently exists only in the form of a web extension. Extension settings are located in
``manifest.json`` inside ``ChatBot-Fin\Extension-ChatBot-Fin\src``.

Front-end
---------
FinGPT Agents' front-end files are located in ``ChatBot-Fin\Extension-ChatBot-Fin\src``.

Currently, ``main.js`` is fully responsible for rendering the extension window, which we call the "pop up".
This long javascript file is organized in three main sections, from top to down:

* **Event Listeners**: Contains functions that handle the extension's communication with back-end, including
  rendering agent's responses, button presses, user input and more.

* **UI**: Contains all code that renders the pop up. Event listener handling "Preferred Links" are also located in this
  section.

* **Dragging**: The function ``makeDraggableAndResizable`` is responsible for making the pop up draggable and resizable.

The task of splitting this file into multiple smaller files is near completion. Documentation will be updated
accordingly once the split is complete.

Plans for Future Front-end Capability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Ability to consistently render LaTeX.

* Integrate DeepSeek.

* With that, nicely render Chain of Thought in the context window if applicable.


.. contents::
   :local:
   :depth: 2

Initial Configuration
~~~~~~~~~~~~~~~~~~~~~

1. **URL and Text Content**:

   - ``currentUrl = window.location.href.toString()``
     Captures the current page URL for logging purposes in the back end.

   - ``textContent = document.body.innerText`` and ``encodedContent = encodeURIComponent(textContent)``
     Retrieves the entire page text and encodes it before sending to the back end.

2. **Available Models**:

   - ``const availableModels = ["o1-preview", "gpt-4o", "deepseek-reasoner"]``
     An array specifying which FinGPT models are available.

   - ``selectedModel = "o1-preview"``
     A default model, selected when the extension loads.

   - ``function getSelectedModel() { return selectedModel; }``
     A helper that returns the currently selected model.

3. **Initial Data Fetch**:

   - A ``fetch`` call to ``/input_webtext/`` at app startup:
     This passes the page’s text content to the back end for any initial processing or indexing, using a ``POST`` request.

User Interface
~~~~~~~~~~~~~~

The interface is composed of the main "popup" window and sub-windows (settings, sources).

1. **Main Popup and Header**:

   - A ``div`` with the id ``draggableElement`` (stored in variable ``popup``) is created to serve as the main container.
   - The top bar (``header``) includes the title "FinGPT" and a small icon container with three icons:

     * **Settings (⚙️)** – Toggles the settings window.
     * **Minimize (➖)** – Collapses the popup.
     * **Close (❌)** – Hides the popup from view.

2. **Introduction Section**:

   - The ``intro`` section features a main heading ("Your personalized financial assistant.") and a subtitle prompting the user to ask a question.

3. **Content and Response Container**:

   - ``#content`` (and within it, ``#respons``) displays the conversation, including user queries and FinGPT answers.

4. **Input Container**:

   - **Mode Buttons**: Allows switching between "Text Mode" and "Image Mode" (tracked by the boolean ``isImageMode``).
   - **Textbox**: An ``<input>`` element for the user’s questions. Pressing Enter triggers a chat response.

5. **Buttons (Ask, Advanced Ask, Clear, Sources)**:

   - **Ask** (simple query)
   - **Advanced Ask** (enables advanced or image-based query handling)
   - **Clear** (clears the current conversation)
   - **Sources** (fetches relevant source URLs from the back end)

6. **Settings Window**:

   - Includes a toggle for Light Mode, a model selection dropdown, and a "Preferred Links" section.
   - **Preferred Links** are user-specified URLs fetched and updated via back-end endpoints.
   - A local RAG toggle (``#ragSwitch``) to decide whether to use retrieved content from locally indexed data.

7. **Sources Window**:

   - Displayed upon clicking "Sources".
   - Shows a loading spinner while fetching relevant links.
   - Lists URLs returned by the back end in a simple format.

API
~~~

All back-end communication is performed through ``fetch`` calls:

1. **Sending Page Content**:

   - ``POST /input_webtext/`` (initial content passing at page load).

2. **Chat Response**:

   - ``GET /get_chat_response/`` for regular queries.
   - ``GET /get_adv_response/`` for advanced queries (with advanced logic or larger context).
   - The model name (e.g., "o1-preview") is appended to the URL.
   - A query parameter ``use_rag`` is read from the local RAG toggle.

3. **Image Processing**:

   - ``POST /process_image/`` if ``isImageMode`` is active.
   - Sends the text prompt for back-end image generation or analysis.

4. **Clearing Messages**:

   - ``POST /clear_messages/`` to reset conversation state in the back end.

5. **Sources Retrieval**:

   - ``GET /get_source_urls/?query=...`` to retrieve relevant web sources for the user’s query.

6. **Logging**:

   - ``GET /log_question/?question=...&button=...&current_url=...`` logs user activity to the back end.

7. **Preferred Links**:

   - ``GET /api/get_preferred_urls/`` loads the user's saved links.
   - ``POST /api/add_preferred_url/`` adds a new link to the user’s preference list.

Button Handlers
~~~~~~~~~~~~~~~

1. **get_chat_response()**:

   - Reads the current input (textbox), checks if it’s non-empty, then calls ``handleChatResponse``.
   - Logs the user’s action as "Ask" in the back end.

2. **get_adv_chat_response()**:

   - Handles either advanced text queries or image-processing mode, based on ``isImageMode``.
   - If ``isImageMode`` is true, calls ``/process_image/``; otherwise, calls ``handleChatResponse`` in advanced mode.
   - Logs "Advanced Ask" in the back end.

3. **clear()**:

   - Clears the response container in the UI and sends a request to ``/clear_messages/`` to reset the server state.

4. **get_sources()**:

   - Opens the Sources Window and fetches relevant links from ``/get_source_urls/``.
   - Displays them as clickable items in the UI.

Helpers
~~~~~~~

1. **appendChatElement(parent, className, text)**:

   - Creates a new DOM element (``<span>``) with the specified CSS class and text.
   - Appends to the designated parent container (e.g., the response area).

2. **handleChatResponse(question, isAdvanced = false)**:

   - The main function for sending user queries and updating the UI with the FinGPT response.
   - Measures response time and logs it to the console.
   - Uses the selected model to look up the appropriate portion of the JSON response.

3. **handleImageResponse(question, description)**:

   - Renders the user’s question and the back-end-generated description in the response container.
   - Used specifically in Image Mode.

4. **logQuestion(question, button)**:

   - Sends an HTTP GET to ``/log_question/`` with the question, which button was pressed, and the current URL.

5. **handleModelSelection(modelItem, modelName)**:

   - Updates the global ``selectedModel`` and highlights the newly chosen model in the settings UI.

6. **makeDraggableAndResizable(element)**:

   - Attaches ``mousedown`` events for dragging or resizing the popup window.
   - Allows the user to move and resize the FinGPT popup, maintaining the sources window position relative to the main popup.


.. note::

   As the code base evolves, this file may be split further, so keep an eye on updates to the front-end structure.
   The information above should offer a decent starting point to understand and modify the existing functionality.

Back-end
--------

FinGPT Agents' back-end files are located in ``ChatBot-Fin\chat_server``. The back-end is hosted via Django with a
couple hand-written Python files. You may see all Django files inside ``chat_server`` (settings.py, urls.py) and
``chat_server_app`` (admin.py, apps,py, models,py, tests,py, views,py). The additional ``datascraper`` folder
contains ``cdm_rag.py``, which is responsible for RAG; and ``datascraper.py``, which contains most back-end functions
and API connection to LLMs.

* All local API endpoints are defined in ``urls.py`` as per standard Django practice.

* Traffic are handled in ``views.py``. Question logging and Preferred URL function are directly handled in this file,
  with all the rest being handled in ``datascraper.py``.

* There are currently no models imported, thus ``models.py`` is empty.


Plans for Back-end
~~~~~~~~~~~~~~~~~~

* Port the locally-hosted back-end to a cloud server (currently decided to be Amazon Lambda).

* Implement the local dynamic database, a.k.a. the local knowledge database.

* Implement langchain.

