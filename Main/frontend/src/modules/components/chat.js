// chat.js
import { get_chat_response, get_adv_chat_response, clear, get_sources } from '../helpers.js';

function createChatInterface(searchQuery) {
    const inputContainer = document.createElement('div');
    inputContainer.id = "inputContainer";

    const modeButtonsContainer = document.createElement('div');
    modeButtonsContainer.id = 'modeButtonsContainer';

    const textModeButton = document.createElement('button');
    textModeButton.id = 'textModeButton';
    textModeButton.innerText = 'Text Mode';
    textModeButton.classList.add('mode-button', 'active-mode');

    modeButtonsContainer.appendChild(textModeButton);
    inputContainer.appendChild(modeButtonsContainer);

    const textbox = document.createElement("input");
    textbox.type = "text";
    textbox.id = "textbox";
    textbox.placeholder = "Type your question here...";
    textbox.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            get_chat_response();
        }
    });
    inputContainer.appendChild(textbox);

    const buttonContainer = document.createElement('div');
    buttonContainer.id = "buttonContainer";

    const askButton = document.createElement('button');
    askButton.id = 'askButton';
    askButton.innerText = "Ask";
    askButton.onclick = get_chat_response;

    const advAskButton = document.createElement('button');
    advAskButton.id = 'advAskButton';
    advAskButton.innerText = "Advanced Ask";
    advAskButton.onclick = get_adv_chat_response;

    buttonContainer.appendChild(askButton);
    buttonContainer.appendChild(advAskButton);

    const buttonRow = document.createElement('div');
    buttonRow.className = "button-row";

    const clearButton = document.createElement('button');
    clearButton.innerText = "Clear";
    clearButton.className = "clear-button";
    clearButton.onclick = clear;

    const sourcesButton = document.createElement('button');
    sourcesButton.innerText = "Sources";
    sourcesButton.className = "sources-button";
    sourcesButton.onclick = function () { get_sources(searchQuery); };

    buttonRow.appendChild(sourcesButton);
    buttonRow.appendChild(clearButton);

    return { inputContainer, buttonContainer, buttonRow };
}

export { createChatInterface };
