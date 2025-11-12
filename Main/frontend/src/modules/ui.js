// ui.js
import { get_chat_response, get_adv_chat_response, makeDraggableAndResizable } from './helpers.js';
import { createPopup } from './components/popup.js';
import { createHeader } from './components/header.js';
import { createChatInterface } from './components/chat.js';
import { createSettingsWindow } from './components/settings_window.js';
import { createLinkManager } from './components/link_manager.js';

const DEFAULT_POPUP_HEIGHT = '520px';
const DEFAULT_POPUP_WIDTH = '690px';

// Function to create UI elements
function createUI() {
    let isFixedMode = true;
    let searchQuery = '';

    const isFixedModeRef = { value: isFixedMode }; // Pass-by-reference workaround

    // Main popup
    const popup = createPopup();

    // Header buttons
    const settingsButton = document.createElement('button');
    settingsButton.innerText = "Settings";
    settingsButton.className = "header-button";

    const positionModeButton = document.createElement('button');
    positionModeButton.innerText = "Hover in Place";
    positionModeButton.id = "position-mode-button";
    positionModeButton.className = "header-button";
    positionModeButton.setAttribute('data-tooltip', 'This toggles this pop up\'s dynamic placement. "Hover in Place" keeps the pop up in place when you scroll the webpage, while "Move with Page" moves the pop up with the page when the page is scrolled.');

    // Settings window
    const settings_window = createSettingsWindow(isFixedModeRef, settingsButton, positionModeButton);

    // Position mode toggle logic
    positionModeButton.onclick = function () {
        const rect = popup.getBoundingClientRect();
        if (isFixedModeRef.value) {
            popup.style.position = "absolute";
            popup.style.top = `${rect.top + window.scrollY}px`;
            popup.style.left = `${rect.left + window.scrollX}px`;
            popup.style.right = "auto"; // Clear right positioning when switching to absolute
            positionModeButton.innerText = "Move with Page";

            const settingsButtonRect = settingsButton.getBoundingClientRect();
            settings_window.style.position = "absolute";
            settings_window.style.top = `${settingsButtonRect.bottom + window.scrollY}px`;
            settings_window.style.left = `${settingsButtonRect.left + window.scrollX - 100}px`;

            // Update sources window position mode
            const sources_window = document.getElementById('sources_window');
            if (sources_window) {
                sources_window.style.position = "absolute";
                sources_window.style.top = `${rect.top + window.scrollY}px`;
                sources_window.style.left = `${rect.left - 370 + window.scrollX}px`; // Keep on left (360px width + 10px gap)
            }
        } else {
            popup.style.position = "fixed";
            popup.style.top = `${rect.top}px`;
            popup.style.left = `${rect.left}px`;
            positionModeButton.innerText = "Hover in Place";

            const settingsButtonRect = settingsButton.getBoundingClientRect();
            settings_window.style.position = "fixed";
            settings_window.style.top = `${settingsButtonRect.bottom}px`;
            settings_window.style.left = `${settingsButtonRect.left - 100}px`;

            // Update sources window position mode
            const sources_window = document.getElementById('sources_window');
            if (sources_window) {
                sources_window.style.position = "fixed";
                sources_window.style.top = `${rect.top}px`;
                sources_window.style.left = `${rect.left - 370}px`; // Keep on left (360px width + 10px gap)
            }
        }
        isFixedModeRef.value = !isFixedModeRef.value;
    };

    // Header
    const header = createHeader(popup, settings_window, settingsButton, positionModeButton, isFixedModeRef, DEFAULT_POPUP_HEIGHT);

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

    const source_urls = document.createElement('div');
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

    const resizeHandleBottomRight = document.createElement('div');
    resizeHandleBottomRight.className = 'resize-handle resize-handle--bottom-right';
    resizeHandleBottomRight.dataset.resizeHandle = 'bottom-right';
    resizeHandleBottomRight.setAttribute('aria-hidden', 'true');
    const resizeHandleBottomLeft = document.createElement('div');
    resizeHandleBottomLeft.className = 'resize-handle resize-handle--bottom-left';
    resizeHandleBottomLeft.dataset.resizeHandle = 'bottom-left';
    resizeHandleBottomLeft.setAttribute('aria-hidden', 'true');

    popup.appendChild(resizeHandleBottomRight);
    popup.appendChild(resizeHandleBottomLeft);

    document.body.appendChild(sources_window);
    document.body.appendChild(settings_window);
    document.body.appendChild(popup);

    // Position + interaction
    popup.style.position = "fixed";
    popup.style.top = "15%";
    // Position dynamically from the right edge
    popup.style.right = "2%";
    popup.style.left = "auto";
    popup.style.width = DEFAULT_POPUP_WIDTH;
    popup.style.height = DEFAULT_POPUP_HEIGHT;

    const sourceWindowOffsetX = 10;
    makeDraggableAndResizable(popup, sourceWindowOffsetX);

    const popupRect = popup.getBoundingClientRect();
    // Position sources window to the left of the main popup
    // Ensure sources window doesn't go off-screen
    const sourcesLeft = Math.max(0, popupRect.left - 370); // 360px width + 10px offset
    sources_window.style.left = `${sourcesLeft}px`;
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
