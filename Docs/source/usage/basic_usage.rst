Basic Usage of the Agent
========================

.. admonition:: When to use this section
   :class: note

   Please make sure the search agent is successfully installed
   and running before testing out any of the examples below!

.. note::
   As a reminder, the search agent currently does NOT work on **Brave** browser.


User Interface
--------------

The search agent's user interface (UI) automatically pops up when user loads any supported website. We generally call
this UI the "pop up". It appears toward the left of the screen and may be *dragged* by holding the top bar or
*resized* by dragging the bottom right corner.

Top Bar
~~~~~~~

The top bar of the pop up contains the following elements:
- **Close Button**: Closes the pop up.
- **Minimize Button**: Minimizes the pop up at its current location.

- **Pin-to-Place Button**: Pins the pop up to its current location. The pop up will not move when the user scrolls the
  page.

- **Setting Button**: Opens the settings page, and may be close by clicking anywhere outside the settings page but
  inside the pop up. It allows users to choose foundation models, set preferred links and toggle the local
  Retrieval-Augmented Generation function. Note, that currently under the local RAG mode, the search agent will NOT
  incorporate context from anywhere but the user's local files.

Main Body
~~~~~~~~~
This part shows the current conversation between the user and the search agent. The search agent currently does not
have any memory—Every prompt is a new conversation.

Prompt Box
~~~~~~~~~~

User may type their prompts inside the prompt box and choose either of the two Ask buttons to send the prompt.
- **Ask Button**: The search agent only incorporates context scraped from the current web page.

- **Advanced Ask Button**: The search agent incorporates context from the current web page as well as any successfully
  scraped user-defined links (Preferred links) and sources returned by the open-domain search. User can monitor the
  searching and scraping logs in real-time through the Terminal/PowerShell window running its back-end.

Two more buttons appear above the prompt box and below where conversations are shown.
- **Clear Button**: Clears the currently shown conversations.

- **Source Button**: Shows the sources used by the search agent to answer the user's prompt. The sources are shown in a
  pop up and may be closed.'

These components make up the current FinGPT Search Agent demo. The documentation will be updated regularly to keep up
with latest progress.