Project Structure
=================

This project currently exists only in the form of a web extension. Extension settings are located in
``manifest.json`` inside ``ChatBot-Fin\Extension-ChatBot-Fin\src``.

Front-end
---------
FinGPT Agents' front-end files are located in ``ChatBot-Fin\Extension-ChatBot-Fin\src``.

Currently, ``content_archive.js`` is fully responsible for rendering the extension window, which we call the "pop up".
This long javascript file is organized in three main sections, from top to down:

* **Event Listeners**: Contains functions that handle the extension's communication with back-end, including
  rendering agent's responses, button presses, user input and more.

* **UI**: Contains all code that renders the pop up. Event listener handling "Preferred Links" are also located in this
  section.

* **Dragging**: The function ``makeDraggableAndResizable`` is responsible for making the pop up draggable and resizable.


Plans for Front-end
~~~~~~~~~~~~~~~~~~~

* Ability to consistently render LaTeX.

* Integrate DeepSeek.

* With that, nicely render Chain of Thought in the context window if applicable.


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

