// helpers.js
import { clearMessages, getSourceUrls, logQuestion } from './api.js';
import { handleChatResponse, handleImageResponse } from './handlers.js';
import { getCachedSources, hasCachedSources, clearCachedSources, getCurrentPageUrl, getCachedSourcesWithoutCurrentPage } from './sourcesCache.js';

// Function to append chat elements
function appendChatElement(parent, className, text) {
    const element = document.createElement('span');
    element.className = className;
    element.innerText = text;
    parent.appendChild(element);
    return element;
}

// Function to clear chat
function clear() {
    const response = document.getElementById('respons');
    const sourceurls = document.getElementById('source_urls');

    // Clear all messages and button rows from the response container
    response.innerHTML = "";

    // Note: We do NOT clear the sources window content because we want to preserve it
    // The sourceurls div will be rebuilt when the user clicks Sources button again

    // Don't clear cached sources - we want to preserve web context
    // clearCachedSources(); // Removed to preserve web context

    clearMessages()
        .then(data => {
            console.log(data);
            const clearMsg = appendChatElement(response, 'system_message', 'Agentic FinSearch: Conversation cleared. Web content context preserved.');
            response.scrollTop = response.scrollHeight;
        })
        .catch(error => {
            console.error('There was a problem clearing messages:', error);
        });
}

// Ask button click
function get_chat_response() {
    const question = document.getElementById('textbox').value;

    if (question) {
        handleChatResponse(question, false);
        logQuestion(question, 'Ask');
        document.getElementById('textbox').value = '';
    } else {
        alert("Please enter a question.");
    }
}

// Advanced Ask button click
function get_adv_chat_response() {
    const question = document.getElementById('textbox').value.trim();

    if (question === '') {
        alert("Please enter a message.");
        return;
    }

    // Clear previous cached sources before making new advanced request
    clearCachedSources();

    // Text Processing Mode
    handleChatResponse(question, true);
    logQuestion(question, 'Advanced Ask');

    document.getElementById('textbox').value = '';
}

// Unified submit function for the new mode selector
function submit_question(mode) {
    const question = document.getElementById('textbox').value.trim();

    if (question === '') {
        alert("Please enter a message.");
        return;
    }

    if (mode === 'Normal') {
        // Normal mode - equivalent to old "Ask" button
        handleChatResponse(question, false);
        logQuestion(question, 'Normal');
    } else if (mode === 'Extensive') {
        // Extensive mode - equivalent to old "Advanced Ask" button
        // Clear previous cached sources before making new advanced request
        clearCachedSources();
        handleChatResponse(question, true);
        logQuestion(question, 'Extensive');
    }

    document.getElementById('textbox').value = '';
}

// Function to get sources
function get_sources(searchQuery) {
    const sources_window = document.getElementById('sources_window');
    const loadingSpinner = document.getElementById('loading_spinner');
    const source_urls = document.getElementById('source_urls');

    console.log('[Sources Debug] get_sources called with query:', searchQuery);
    sources_window.style.display = 'block';

    // Hide spinner and show source URLs container
    loadingSpinner.style.display = 'none';
    source_urls.style.display = 'block';

    // Get current page and other sources
    const currentPageUrl = getCurrentPageUrl();
    const otherSources = getCachedSourcesWithoutCurrentPage();

    console.log('[Sources Debug] Current page URL:', currentPageUrl);
    console.log('[Sources Debug] Other sources:', otherSources);

    // Clear and rebuild the source URLs display
    source_urls.innerHTML = '';

    // ALWAYS create "Current active webpage" section
    const currentPageSection = document.createElement('div');
    currentPageSection.className = 'source-section';

    const currentPageHeader = document.createElement('div');
    currentPageHeader.className = 'source-section-header';
    currentPageHeader.innerText = 'Current active webpage';
    currentPageSection.appendChild(currentPageHeader);

    const currentPageContent = document.createElement('ul');
    currentPageContent.className = 'source-section-content';

    if (currentPageUrl) {
        const link = document.createElement('a');
        link.href = currentPageUrl;
        link.innerText = currentPageUrl;
        link.target = "_blank";

        const listItem = document.createElement('li');
        listItem.appendChild(link);
        currentPageContent.appendChild(listItem);
    } else {
        const emptyMsg = document.createElement('div');
        emptyMsg.className = 'empty-sources';
        emptyMsg.innerText = 'No current webpage detected';
        currentPageContent.appendChild(emptyMsg);
    }

    currentPageSection.appendChild(currentPageContent);
    source_urls.appendChild(currentPageSection);

    // ALWAYS create "Sources used" section
    const sourcesSection = document.createElement('div');
    sourcesSection.className = 'source-section';

    const sourcesHeader = document.createElement('div');
    sourcesHeader.className = 'source-section-header';
    sourcesHeader.innerText = 'Sources used';
    sourcesSection.appendChild(sourcesHeader);

    const sourcesContent = document.createElement('ul');
    sourcesContent.className = 'source-section-content';

    if (otherSources.length > 0) {
        otherSources.forEach((url, idx) => {
            console.log(`[Sources Debug] Displaying source URL ${idx + 1}: ${url}`);
            if (url.includes('duckduckgo')) {
                console.warn(`[Sources Debug] WARNING: DuckDuckGo URL being displayed at index ${idx}: ${url}`);
            }

            const link = document.createElement('a');
            link.href = url;
            link.innerText = url;
            link.target = "_blank";

            const listItem = document.createElement('li');
            listItem.appendChild(link);
            sourcesContent.appendChild(listItem);
        });
    } else {
        const emptyMsg = document.createElement('div');
        emptyMsg.className = 'empty-sources';
        emptyMsg.innerText = 'Sources used for agent responses when using Advanced Ask is displayed here.';
        sourcesContent.appendChild(emptyMsg);
    }

    sourcesSection.appendChild(sourcesContent);
    source_urls.appendChild(sourcesSection);
}

// Removed old preferred links functions - now handled by link_manager.js component

// Function to make an element draggable and resizable
function makeDraggableAndResizable(element, sourceWindowOffsetX = 10, isFixedMode = false) {
    let isDragging = false;
    let isResizing = false;
    let offsetX, offsetY, startX, startY, startWidth, startHeight;

    element.querySelector('.draggable').addEventListener('mousedown', function(e) {
        if (['INPUT', 'TEXTAREA', 'BUTTON', 'A'].includes(e.target.tagName) || 'position-mode-icon' === e.target.id) {
            return;
        }

        e.preventDefault();

        const rect = element.getBoundingClientRect();
        const isRightEdge = e.clientX > rect.right - 10;
        const isBottomEdge = e.clientY > rect.bottom - 10;

        if (isRightEdge || isBottomEdge) {
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = rect.width;
            startHeight = rect.height;
            document.addEventListener('mousemove', resizeElement);
        } else {
            isDragging = true;
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            document.addEventListener('mousemove', dragElement);
        }

        document.addEventListener('mouseup', closeDragOrResizeElement);
    });

    function dragElement(e) {
        e.preventDefault();
        const newX = e.clientX - offsetX + (isFixedMode ? 0 : window.scrollX);
        const newY = e.clientY - offsetY + (isFixedMode ? 0 : window.scrollY);
        element.style.left = `${newX}px`;
        element.style.top = `${newY}px`;

        // Move sources window with main popup
        const sourcesWindow = document.getElementById('sources_window');
        sourcesWindow.style.left = `${newX + element.offsetWidth + sourceWindowOffsetX}px`;
        sourcesWindow.style.top = `${newY}px`;
    }

    function resizeElement(e) {
        e.preventDefault();
        const newWidth = startWidth + (e.clientX - startX);
        const newHeight = startHeight + (e.clientY - startY);
        if (newWidth > 250) {
            element.style.width = `${newWidth}px`;
        }
        if (newHeight > 300) {
            element.style.height = `${newHeight}px`;
        }

        // Move sources window with main popup
        const sourcesWindow = document.getElementById('sources_window');
        sourcesWindow.style.left = `${element.offsetLeft + element.offsetWidth + sourceWindowOffsetX}px`;
    }

    function closeDragOrResizeElement() {
        document.removeEventListener('mousemove', dragElement);
        document.removeEventListener('mousemove', resizeElement);
        document.removeEventListener('mouseup', closeDragOrResizeElement);
        isDragging = false;
        isResizing = false;
    }
}

export { appendChatElement, clear, get_chat_response, get_adv_chat_response, submit_question, get_sources,
    makeDraggableAndResizable };