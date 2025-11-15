// ui.js
import { get_chat_response, get_adv_chat_response, makeDraggableAndResizable } from './helpers.js';
import { createPopup } from './components/popup.js';
import { createHeader } from './components/header.js';
import { createChatInterface } from './components/chat.js';
import { createSettingsWindow } from './components/settings_window.js';
import { createLinkManager } from './components/link_manager.js';
import { getLayoutKeyForUrl, loadLayoutState, saveLayoutState } from './layoutState.js';

const DEFAULT_POPUP_HEIGHT = '520px';
const DEFAULT_POPUP_WIDTH = '690px';

function capturePopupLayout(element, isFixedMode) {
    const rect = element.getBoundingClientRect();
    return {
        position: isFixedMode ? 'fixed' : 'absolute',
        top: isFixedMode ? rect.top : rect.top + window.scrollY,
        left: isFixedMode ? rect.left : rect.left + window.scrollX,
        width: rect.width,
        height: rect.height,
    };
}

// Function to create UI elements
function createUI() {
    let isFixedMode = true;
    let searchQuery = '';
    const layoutStorageKey = getLayoutKeyForUrl(window.location.href);

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

    const updateSettingsWindowPosition = () => {
        const settingsButtonRect = settingsButton.getBoundingClientRect();
        const offsetY = isFixedModeRef.value ? 0 : window.scrollY;
        const offsetX = isFixedModeRef.value ? 0 : window.scrollX;
        settings_window.style.position = isFixedModeRef.value ? "fixed" : "absolute";
        settings_window.style.top = `${settingsButtonRect.bottom + offsetY}px`;
        settings_window.style.left = `${settingsButtonRect.left - 100 + offsetX}px`;
    };

    const updateSourcesWindowPosition = () => {
        const sources_window = document.getElementById('sources_window');
        if (!sources_window) {
            return;
        }
        const popupRect = popup.getBoundingClientRect();
        const baseLeft = isFixedModeRef.value ? popupRect.left : popup.offsetLeft;
        const baseTop = isFixedModeRef.value ? popupRect.top : popup.offsetTop;
        sources_window.style.position = isFixedModeRef.value ? 'fixed' : 'absolute';
        const sourcesLeft = Math.max(0, baseLeft - 370); // 360px width + 10px gap
        sources_window.style.left = `${sourcesLeft}px`;
        sources_window.style.top = `${baseTop}px`;
    };

    const persistLayoutState = () => {
        const layoutState = capturePopupLayout(popup, isFixedModeRef.value);
        saveLayoutState(layoutState, layoutStorageKey).catch((error) => {
            console.warn('Unable to persist popup layout:', error);
        });
    };

    const applySavedLayout = (layoutState) => {
        if (!layoutState) {
            return;
        }
        isFixedModeRef.value = layoutState.position !== 'absolute';
        popup.style.position = isFixedModeRef.value ? 'fixed' : 'absolute';
        popup.style.top = `${layoutState.top}px`;
        popup.style.left = `${layoutState.left}px`;
        popup.style.right = 'auto';
        if (layoutState.width) {
            popup.style.width = `${layoutState.width}px`;
        }
        if (layoutState.height) {
            popup.style.height = `${layoutState.height}px`;
        }
        positionModeButton.innerText = isFixedModeRef.value ? "Hover in Place" : "Move with Page";
        requestAnimationFrame(() => {
            updateSettingsWindowPosition();
            updateSourcesWindowPosition();
        });
    };

    // Position mode toggle logic
    positionModeButton.onclick = function () {
        const rect = popup.getBoundingClientRect();
        if (isFixedModeRef.value) {
            popup.style.position = "absolute";
            popup.style.top = `${rect.top + window.scrollY}px`;
            popup.style.left = `${rect.left + window.scrollX}px`;
        } else {
            popup.style.position = "fixed";
            popup.style.top = `${rect.top}px`;
            popup.style.left = `${rect.left}px`;
        }
        popup.style.right = "auto";
        isFixedModeRef.value = !isFixedModeRef.value;
        positionModeButton.innerText = isFixedModeRef.value ? "Hover in Place" : "Move with Page";
        updateSettingsWindowPosition();
        updateSourcesWindowPosition();
        persistLayoutState();
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
    updateSettingsWindowPosition();
    updateSourcesWindowPosition();

    const sourceWindowOffsetX = 10;
    makeDraggableAndResizable(popup, sourceWindowOffsetX, () => {
        updateSettingsWindowPosition();
        persistLayoutState();
    });

    loadLayoutState(layoutStorageKey).then((layoutState) => {
        if (layoutState) {
            applySavedLayout(layoutState);
        }
        persistLayoutState();
    });

    console.log("initalized");

    return {
        popup,
        settings_window,
        sources_window,
        searchQuery,
    };
}

export { get_chat_response, get_adv_chat_response, createUI };
