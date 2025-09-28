// helpers.js
import { clearMessages, getSourceUrls, addPreferredUrl, getPreferredUrls, logQuestion } from './api.js';
import { handleChatResponse, handleImageResponse } from './handlers.js';
import { getCachedSources, hasCachedSources, clearCachedSources } from './sourcesCache.js';

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

    response.innerHTML = "";
    if (sourceurls) {
        sourceurls.innerHTML = "";
    }

    // Clear cached sources when clearing conversation
    clearCachedSources();

    clearMessages()
        .then(data => {
            console.log(data);
            const clearMsg = appendChatElement(response, 'system_message', 'FinGPT: Conversation cleared. Web content context preserved.');
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

// Function to get sources
function get_sources(searchQuery) {
    const sources_window = document.getElementById('sources_window');
    const loadingSpinner = document.getElementById('loading_spinner');
    const source_urls = document.getElementById('source_urls');

    sources_window.style.display = 'block';

    // Check if we have cached sources first
    if (hasCachedSources()) {
        console.log('Using cached sources for instant display');
        const cachedUrls = getCachedSources();

        // Display cached sources immediately without loading
        source_urls.innerHTML = '';
        cachedUrls.forEach(url => {
            const link = document.createElement('a');
            link.href = url;
            link.innerText = url;
            link.target = "_blank";

            const listItem = document.createElement('li');
            listItem.appendChild(link);
            listItem.classList.add('source-item');

            source_urls.appendChild(listItem);
        });

        // Show sources immediately without spinner
        loadingSpinner.style.display = 'none';
        source_urls.style.display = 'block';

        // Optionally, still fetch from backend to get icons (but don't show spinner)
        getSourceUrls(searchQuery)
            .then(data => {
                // If backend returns sources with icons, update the display
                if (data["resp"] && data["resp"].length > 0) {
                    console.log('Updating sources with icons from backend');
                    source_urls.innerHTML = '';
                    data["resp"].forEach(source => {
                        const url = source[0];
                        const icon = source[1]; // Icon URL if available

                        const link = document.createElement('a');
                        link.href = url;
                        link.innerText = url;
                        link.target = "_blank";

                        const listItem = document.createElement('li');
                        listItem.appendChild(link);
                        listItem.classList.add('source-item');

                        source_urls.appendChild(listItem);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching source icons:', error);
                // Cached sources are still displayed, so no problem
            });
    } else {
        // No cached sources, fetch from backend with loading spinner
        loadingSpinner.style.display = 'block';
        source_urls.style.display = 'none';

        getSourceUrls(searchQuery)
            .then(data => {
                console.log(data["resp"]);
                const sources = data["resp"];
                source_urls.innerHTML = '';

                sources.forEach(source => {
                    const url = source[0];
                    const link = document.createElement('a');
                    link.href = url;
                    link.innerText = url;
                    link.target = "_blank";

                    const listItem = document.createElement('li');
                    listItem.appendChild(link);
                    listItem.classList.add('source-item');

                    source_urls.appendChild(listItem);
                });

                loadingSpinner.style.display = 'none'; // Hide spinner
                source_urls.style.display = 'block'; // Show source list
            })
            .catch(error => {
                console.error('There was a problem getting sources:', error);
                loadingSpinner.style.display = 'none'; // Hide spinner in case of error
            });
    }
}

// Function to load preferred links
function loadPreferredLinks() {
    getPreferredUrls()
        .then(data => {
            const preferredLinksContent = document.getElementById('preferred_links_content');
            preferredLinksContent.innerHTML = ''; // Clear existing content
            
            if (data.urls.length > 0) {
                data.urls.forEach(link => {
                    const linkItem = document.createElement('div');
                    linkItem.className = 'preferred-link-item';
                    linkItem.innerText = link;
                    preferredLinksContent.appendChild(linkItem);
                });
            }
            
            // Re-add the '+' button
            const addLinkButton = document.getElementById('add_link_button') || createAddLinkButton();
            preferredLinksContent.appendChild(addLinkButton);
        })
        .catch(error => console.error('Error loading preferred links:', error));
}

// Function to create Add Link Button
function createAddLinkButton() {
    const addLinkButton = document.createElement('div');
    addLinkButton.id = "add_link_button";
    addLinkButton.innerText = "+";
    addLinkButton.onclick = function() {
        const newLink = prompt("Enter a new preferred URL:");
        if (newLink) {
            addPreferredUrl(newLink)
                .then(data => {
                    if (data.status === 'success') {
                        const preferredLinksContent = document.getElementById('preferred_links_content');
                        const newLinkItem = document.createElement('div');
                        newLinkItem.className = 'preferred-link-item';
                        newLinkItem.innerText = newLink;
                        preferredLinksContent.insertBefore(newLinkItem, addLinkButton);
                    } else {
                        alert('Failed to add the new URL.');
                    }
                })
                .catch(error => console.error('Error adding preferred link:', error));
        }
    };
    return addLinkButton;
}

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

export { appendChatElement, clear, get_chat_response, get_adv_chat_response, get_sources, 
    loadPreferredLinks, createAddLinkButton, makeDraggableAndResizable };