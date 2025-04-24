// ui.js
import { get_chat_response, get_adv_chat_response, makeDraggableAndResizable } from './helpers.js';
import { createPopup } from './components/popup.js';
import { createHeader } from './components/header.js';
import { createChatInterface } from './components/chat.js';
import { createSettingsWindow } from './components/settings_window.js';

// Function to create UI elements
function createUI() {
    let isFixedMode = false;
    let searchQuery = '';

    const isFixedModeRef = { value: isFixedMode }; // Pass-by-reference workaround

    // Main popup
    const popup = createPopup();

    // Icons
    const settingsIcon = document.createElement('span');
    settingsIcon.innerText = "⚙️";
    settingsIcon.className = "icon";

    const positionModeIcon = document.createElement('span');
    positionModeIcon.innerText = "📌";
    positionModeIcon.id = "position-mode-icon";
    positionModeIcon.className = "icon";

    // Settings window
    const settings_window = createSettingsWindow(isFixedModeRef, settingsIcon, positionModeIcon);

    // Position mode toggle logic
    positionModeIcon.onclick = function () {
        const rect = popup.getBoundingClientRect();
        if (isFixedModeRef.value) {
            popup.style.position = "absolute";
            popup.style.top = `${rect.top + window.scrollY}px`;
            popup.style.left = `${rect.left + window.scrollX}px`;
            positionModeIcon.innerText = "📌";

            const settingsIconRect = settingsIcon.getBoundingClientRect();
            settings_window.style.position = "absolute";
            settings_window.style.top = `${settingsIconRect.bottom + window.scrollY}px`;
            settings_window.style.left = `${settingsIconRect.left + window.scrollX}px`;
        } else {
            popup.style.position = "fixed";
            popup.style.top = `${rect.top}px`;
            popup.style.left = `${rect.left}px`;
            positionModeIcon.innerText = "⛓️‍💥";

            const settingsIconRect = settingsIcon.getBoundingClientRect();
            settings_window.style.position = "fixed";
            settings_window.style.top = `${settingsIconRect.bottom}px`;
            settings_window.style.left = `${settingsIconRect.left}px`;
        }
        isFixedModeRef.value = !isFixedModeRef.value;
    };

    // Header
    const header = createHeader(popup, settings_window, settingsIcon, positionModeIcon, isFixedModeRef);

    // Intro
    const intro = document.createElement('div');
    intro.id = "intro";

    const titleText = document.createElement('h2');
    titleText.innerText = "Your personalized financial assistant.";

    const subtitleText = document.createElement('p');
    subtitleText.id = "subtitleText";
    subtitleText.innerText = "Ask me something!";

    intro.appendChild(subtitleText);
    intro.appendChild(titleText);
    intro.appendChild(subtitleText);

    // Chat area
    const content = document.createElement('div');
    content.id = "content";
    const responseContainer = document.createElement('div');
    responseContainer.id = "respons";
    content.appendChild(responseContainer);

    const { inputContainer, buttonContainer, buttonRow } = createChatInterface(searchQuery);

    // Sources window
    const sources_window = document.createElement('div');
    sources_window.id = "sources_window";
    sources_window.style.display = 'none';

    const sourcesHeader = document.createElement('div');
    sourcesHeader.id = "sources_window_header";

    const sourcesTitle = document.createElement('h2');
    sourcesTitle.innerText = "Sources";

    const sourcesCloseIcon = document.createElement('span');
    sourcesCloseIcon.innerText = "❌";
    sourcesCloseIcon.className = "icon";
    sourcesCloseIcon.onclick = function () {
        sources_window.style.display = 'none';
    };

    sourcesHeader.appendChild(sourcesTitle);
    sourcesHeader.appendChild(sourcesCloseIcon);

    const loadingSpinner = document.createElement('div');
    loadingSpinner.id = "loading_spinner";
    loadingSpinner.className = "spinner";
    loadingSpinner.style.display = 'none';

    const source_urls = document.createElement('ul');
    source_urls.id = "source_urls";

    sources_window.appendChild(sourcesHeader);
    sources_window.appendChild(loadingSpinner);
    sources_window.appendChild(source_urls);

    // Mount everything
    popup.appendChild(header);
    popup.appendChild(intro);
    popup.appendChild(content);
    popup.appendChild(buttonRow);
    popup.appendChild(inputContainer);
    popup.appendChild(buttonContainer);

    document.body.appendChild(sources_window);
    document.body.appendChild(settings_window);
    document.body.appendChild(popup);

    // Position + interaction
    popup.style.position = "absolute";
    popup.style.top = "10%";
    popup.style.left = "10%";
    popup.style.width = '450px';
    popup.style.height = '650px';

    const sourceWindowOffsetX = 10;
    makeDraggableAndResizable(popup, sourceWindowOffsetX, isFixedModeRef.value);

    const popupRect = popup.getBoundingClientRect();
    sources_window.style.left = `${popupRect.right + sourceWindowOffsetX}px`;
    sources_window.style.top = `${popupRect.top}px`;

    console.log("initalized");

    return {
        popup,
        settings_window,
        sources_window,
        searchQuery,
    };
}

export { get_chat_response, get_adv_chat_response, createUI };
