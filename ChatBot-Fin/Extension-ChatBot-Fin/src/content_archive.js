// content_archive.js

const currentUrl = window.location.href.toString();
console.log("Current page: ", currentUrl);

const textContent = document.body.innerText || "";
const encodedContent = encodeURIComponent(textContent);

// Available models
const availableModels = ["o1-preview", "gpt-4o", "deepseek-reasoner"];

// Initialize a single selected model
let selectedModel = "o1-preview";

function getSelectedModel() {
    return selectedModel;
}

// POST JSON to the server endpoint
fetch("http://127.0.0.1:8000/input_webtext/", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
    },
    body: JSON.stringify({
        textContent: textContent,
        currentUrl: currentUrl
    }),
})
    .then(response => {
        if (!response.ok) {
            throw new Error(`Network response was not ok (status: ${response.status})`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Response from server:", data);
    })
    .catch(error => {
        console.error("There was a problem with your fetch operation:", error);
    });


// Function to create and append chat elements
function appendChatElement(parent, className, text) {
    const element = document.createElement('span');
    element.className = className;
    element.innerText = text;
    parent.appendChild(element);
    return element;
}

// Function to handle chat responses (single model)
function handleChatResponse(question, isAdvanced = false) {
    const startTime = performance.now();
    const responseContainer = document.getElementById('respons');

    // Show the user's question
    appendChatElement(responseContainer, 'your_question', question);

    // Placeholder "Loading..." text
    const loadingElement = appendChatElement(
        responseContainer,
        'agent_response',
        `FinGPT: Loading...`
    );

    // Encode question and decide endpoint
    const encodedQuestion = encodeURIComponent(question);
    const endpoint = isAdvanced ? 'get_adv_response' : 'get_chat_response';

    // Read the RAG checkbox state
    const useRAG = document.getElementById('ragSwitch').checked;

    fetch(
        `http://127.0.0.1:8000/${endpoint}/?question=${encodedQuestion}&models=${selectedModel}&is_advanced=${isAdvanced}&use_rag=${useRAG}`,
        { method: 'GET' }
    )
        .then(response => response.json())
        .then(data => {
            const endTime = performance.now();
            const responseTime = endTime - startTime;
            console.log(`Time taken for response: ${responseTime} ms`);

            // Get the response for the selected model
            const modelResponse = data.resp[selectedModel];

            if (!modelResponse) {
                // Safeguard in case backend does not return something
                loadingElement.innerText = `FinGPT: (No response from server)`;
            } else if (modelResponse.startsWith("The following file(s) are missing")) {
                loadingElement.innerText = `FinGPT: Error - ${modelResponse}`;
            } else {
                loadingElement.innerText = `FinGPT: ${modelResponse}`;
            }

            // Clear the user textbox
            document.getElementById('textbox').value = '';
            responseContainer.scrollTop = responseContainer.scrollHeight;
        })
        .catch(error => {
            console.error('There was a problem with your fetch operation:', error);
            loadingElement.innerText = `FinGPT: Failed to load response.`;
        });
}

// Ask button click
function get_chat_response() {
    const question = document.getElementById('textbox').value.trim();

    if (question) {
        handleChatResponse(question, false);
        logQuestion(question, 'Ask');
        document.getElementById('textbox').value = '';
    } else {
        alert("Please enter a question.");
    }
}

let searchQuery = '';

// Advanced Ask button click
function get_adv_chat_response() {
    const question = document.getElementById('textbox').value.trim();

    if (question === '') {
        alert("Please enter a message.");
        return;
    }

    // if (isImageMode) {
        // Image Processing Mode
    //     fetch('http://127.0.0.1:8000/process_image/', {
    //         method: 'POST',
    //         headers: { 'Content-Type': 'application/json' },
    //         body: JSON.stringify({ 'text_prompt': question })
    //     })
    //         .then(response => response.json())
    //         .then(data => {
    //             if (data.status === 'success') {
    //                 handleImageResponse(question, data.description);
    //             } else {
    //                 alert('Failed to process image.');
    //             }
    //         })
    //         .catch(error => {
    //             console.error('Error processing image:', error);
    //         });
    // } else {
        // Text Processing Mode
        handleChatResponse(question, true);
        logQuestion(question, 'Advanced Ask');
    // }

    document.getElementById('textbox').value = '';
}

// Function to handle image response
// function handleImageResponse(question, description) {
//     const responseContainer = document.getElementById('respons');
//     appendChatElement(responseContainer, 'your_question', question);
//
//     const responseDiv = document.createElement('div');
//     responseDiv.className = 'agent_response';
//     responseDiv.innerText = description;
//     responseContainer.appendChild(responseDiv);
//
//     responseContainer.scrollTop = responseContainer.scrollHeight;
// }

function clear() {
    const response = document.getElementById('respons');
    const sourceurls = document.getElementById('source_urls');

    response.innerHTML = "";
    if (sourceurls) {
        sourceurls.innerHTML = "";
    }
    fetch(`http://127.0.0.1:8000/clear_messages/`, { method: "POST" })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log(data);
        })
        .catch(error => {
            console.error('There was a problem with your fetch operation:', error);
        });
}

// Function to get sources
function get_sources(search_query) {
    console.log("get_sources called with query:", search_query);
    const sources_window = document.getElementById('sources_window');
    const loadingSpinner = document.getElementById('loading_spinner');
    const source_urls = document.getElementById('source_urls');

    sources_window.style.display = 'block';
    loadingSpinner.style.display = 'block';
    source_urls.style.display = 'none';

    fetch(`http://127.0.0.1:8000/get_source_urls/?query=${encodeURIComponent(String(search_query))}`, { method: "GET" })
        .then(response => response.json())
        .then(data => {
            console.log("Response from server:", data["resp"]);
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

            loadingSpinner.style.display = 'none';
            source_urls.style.display = 'block';
        })
        .catch(error => {
            console.error('There was a problem with your fetch operation:', error);
            loadingSpinner.style.display = 'none';
        });
}


// Function to log question
function logQuestion(question, button) {
    const currentUrl = window.location.href;

    fetch(
        `http://127.0.0.1:8000/log_question/?question=${encodeURIComponent(question)}&button=${encodeURIComponent(button)}&current_url=${encodeURIComponent(currentUrl)}`,
        { method: "GET" }
    )
        .then(response => response.json())
        .then(data => {
            if (data.status !== 'success') {
                console.error('Failed to log question');
            }
        })
        .catch(error => {
            console.error('Error logging question:', error);
        });
}

// Main popup
const popup = document.createElement('div');
popup.id = "draggableElement";

// Header
const header = document.createElement('div');
header.id = "header";
header.className = "draggable";

const title = document.createElement('span');
title.innerText = "FinGPT";

// Icon container
const iconContainer = document.createElement('div');
iconContainer.id = "icon-container";

const settingsIcon = document.createElement('span');
settingsIcon.innerText = "⚙️";
settingsIcon.className = "icon";

const positionModeIcon = document.createElement('span');
positionModeIcon.innerText = "📌";
positionModeIcon.id = "position-mode-icon";
positionModeIcon.className = "icon";
positionModeIcon.onclick = function () {
    if (isFixedMode) {
        // switch to absolute positioning
        const rect = popup.getBoundingClientRect();

        const newX = rect.left + window.scrollX
        const newY = rect.top + window.scrollY

        popup.style.position = "absolute";
        popup.style.top = `${newY}px`;
        popup.style.left = `${newX}px`;
        positionModeIcon.innerText = "📌";

        // settings window positioning update
        const settingsIconRect = settingsIcon.getBoundingClientRect();
        settings_window.style.position = "absolute";
        settings_window.style.top = `${settingsIconRect.bottom + window.scrollY}px`;
        settings_window.style.left = `${settingsIconRect.left + window.scrollX}px`;
    } else {
        // switch to fixed positioning
        const rect = popup.getBoundingClientRect();
        popup.style.position = "fixed";
        popup.style.top = `${rect.top}px`;
        popup.style.left = `${rect.left}px`;
        positionModeIcon.innerText = "⛓️‍💥";

        // settings window positioning update
        const settingsIconRect = settingsIcon.getBoundingClientRect();
        settings_window.style.position = "fixed";
        settings_window.style.top = `${settingsIconRect.bottom}px`;
        settings_window.style.left = `${settingsIconRect.left}px`;
    }
    isFixedMode = !isFixedMode; // toggle the mode
}

const minimizeIcon = document.createElement('span');
minimizeIcon.innerText = "➖";
minimizeIcon.className = "icon";
minimizeIcon.onclick = function() {
    if (popup.classList.contains('minimized')) {
        popup.classList.remove('minimized');
        popup.style.height = '600px';
    } else {
        popup.classList.add('minimized');
        popup.style.height = '60px';
    }
};

const closeIcon = document.createElement('span');
closeIcon.innerText = "❌";
closeIcon.className = "icon";
closeIcon.onclick = function() {
    popup.style.display = 'none';
};

iconContainer.appendChild(settingsIcon);
iconContainer.appendChild(positionModeIcon);
iconContainer.appendChild(minimizeIcon);
iconContainer.appendChild(closeIcon);

header.appendChild(title);
header.appendChild(iconContainer);

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

const content = document.createElement('div');
content.id = "content";

const responseContainer = document.createElement('div');
responseContainer.id = "respons";
content.appendChild(responseContainer);

// Input container
const inputContainer = document.createElement('div');
inputContainer.id = "inputContainer";

// Create mode buttons
const modeButtonsContainer = document.createElement('div');
modeButtonsContainer.id = 'modeButtonsContainer';

const textModeButton = document.createElement('button');
textModeButton.id = 'textModeButton';
textModeButton.innerText = 'Text Mode';
textModeButton.classList.add('mode-button', 'active-mode');

// const imageModeButton = document.createElement('button');
// imageModeButton.id = 'imageModeButton';
// imageModeButton.innerText = 'Image Mode';
// imageModeButton.classList.add('mode-button');

modeButtonsContainer.appendChild(textModeButton);
// modeButtonsContainer.appendChild(imageModeButton);

inputContainer.appendChild(modeButtonsContainer);

// Textbox
const textbox = document.createElement("input");
textbox.type = "text";
textbox.id = "textbox";
textbox.placeholder = "Type your question here...";

inputContainer.appendChild(textbox);

// Bind Enter key to get_chat_response()
textbox.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        get_chat_response();
    }
});

// Initialize isImageMode
// let isImageMode = false;

textModeButton.addEventListener('click', function() {
    // isImageMode = false;
    textModeButton.classList.add('active-mode');
    // imageModeButton.classList.remove('active-mode');
});

// imageModeButton.addEventListener('click', function() {
//     isImageMode = true;
//     imageModeButton.classList.add('active-mode');
//     textModeButton.classList.remove('active-mode');
// });

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
sourcesButton.onclick = function() {
    console.log("Sources button clicked");
    const query = typeof searchQuery !== 'undefined' ? searchQuery : "";
    console.log("Using search query:", query);
    get_sources(query);
};

buttonRow.appendChild(sourcesButton);
buttonRow.appendChild(clearButton);

popup.appendChild(header);
popup.appendChild(intro);
popup.appendChild(content);
popup.appendChild(buttonRow);
popup.appendChild(inputContainer);
popup.appendChild(buttonContainer);

// Settings Window
const settings_window = document.createElement('div');
settings_window.style.display = "none";
settings_window.id = "settings_window";

// Light Mode Toggle
const settingsLabel = document.createElement('label');
settingsLabel.innerText = "Light Mode";

const lightModeSwitch = document.createElement('input');
lightModeSwitch.type = "checkbox";
lightModeSwitch.onchange = function() {
    document.body.classList.toggle('light-mode');
};

settingsLabel.appendChild(lightModeSwitch);
settings_window.appendChild(settingsLabel);

// Model Selection Section
const modelSelectionContainer = document.createElement('div');
modelSelectionContainer.id = "model_selection_container";

const modelSelectionHeader = document.createElement('div');
modelSelectionHeader.id = "model_selection_header";
modelSelectionHeader.innerText = `Model: ${selectedModel}`;

const modelToggleIcon = document.createElement('span');
modelToggleIcon.innerText = "⯆";

modelSelectionHeader.appendChild(modelToggleIcon);
modelSelectionContainer.appendChild(modelSelectionHeader);

const modelSelectionContent = document.createElement('div');
modelSelectionContent.id = "model_selection_content";
modelSelectionContent.style.display = "none";

// Handle model selection (only one at a time)
function handleModelSelection(modelItem, modelName) {
    // Deselect all items
    const allItems = document.querySelectorAll('.model-selection-item');
    allItems.forEach(item => item.classList.remove('selected-model'));

    // Set selectedModel and mark the clicked item
    selectedModel = modelName;
    modelItem.classList.add('selected-model');

    modelSelectionHeader.innerText = `Model: ${selectedModel}`;
    modelSelectionHeader.appendChild(modelToggleIcon);
}

// Create a model selection item for each available model
availableModels.forEach(model => {
    const modelItem = document.createElement('div');
    modelItem.className = 'model-selection-item';
    modelItem.innerText = model;

    // Default selected model
    if (model === selectedModel) {
        modelItem.classList.add('selected-model');
    }

    modelItem.onclick = function() {
        handleModelSelection(modelItem, model);
    };
    modelSelectionContent.appendChild(modelItem);
});

modelSelectionContainer.appendChild(modelSelectionContent);
settings_window.appendChild(modelSelectionContainer);

// Toggle Model Selection Section
modelSelectionHeader.onclick = function() {
    if (modelSelectionContent.style.display === "none") {
        modelSelectionContent.style.display = "block";
        modelToggleIcon.innerText = "⯅";
    } else {
        modelSelectionContent.style.display = "none";
        modelToggleIcon.innerText = "⯆";
    }
};

// Preferred Links Section
const preferredLinksContainer = document.createElement('div');
preferredLinksContainer.id = "preferred_links_container";

const preferredLinksHeader = document.createElement('div');
preferredLinksHeader.id = "preferred_links_header";
preferredLinksHeader.innerText = "Preferred Links";

const toggleIcon = document.createElement('span');
toggleIcon.innerText = "⯆";  // Down arrow

preferredLinksHeader.appendChild(toggleIcon);
preferredLinksContainer.appendChild(preferredLinksHeader);

const preferredLinksContent = document.createElement('div');
preferredLinksContent.id = "preferred_links_content";

// Add Link Button
const addLinkButton = document.createElement('div');
addLinkButton.id = "add_link_button";
addLinkButton.innerText = "+";
addLinkButton.onclick = function() {
    const newLink = prompt("Enter a new preferred URL:");
    if (newLink) {
        // Send the new link to the backend
        fetch('http://127.0.0.1:8000/api/add_preferred_url/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `url=${encodeURIComponent(newLink)}`
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const newLinkItem = document.createElement('div');
                    newLinkItem.className = 'preferred-link-item';
                    newLinkItem.innerText = newLink;
                    preferredLinksContent.appendChild(newLinkItem);
                } else {
                    alert('Failed to add the new URL.');
                }
            })
            .catch(error => console.error('Error adding preferred link:', error));
    }
};

// Load existing preferred links when the settings window is opened
function loadPreferredLinks() {
    fetch('http://127.0.0.1:8000/api/get_preferred_urls/')
        .then(response => response.json())
        .then(data => {
            preferredLinksContent.innerHTML = ''; // Clear existing content
            if (data.urls.length > 0) {
                data.urls.forEach(link => {
                    const linkItem = document.createElement('div');
                    linkItem.className = 'preferred-link-item';
                    linkItem.innerText = link;
                    preferredLinksContent.appendChild(linkItem);
                });
            }
            preferredLinksContent.appendChild(addLinkButton); // Add the '+' button
        })
        .catch(error => console.error('Error loading preferred links:', error));
}

// Local RAG Toggle
const ragLabel = document.createElement('label');
ragLabel.innerText = "Local RAG";

const ragSwitch = document.createElement('input');
ragSwitch.type = "checkbox";
ragSwitch.id = "ragSwitch";
ragSwitch.onchange = function() {
    // Any immediate actions when the checkbox changes can be handled here
};

ragLabel.appendChild(ragSwitch);

preferredLinksContent.appendChild(addLinkButton);
preferredLinksContainer.appendChild(preferredLinksContent);
settings_window.appendChild(preferredLinksContainer);
settings_window.appendChild(ragLabel);

document.body.appendChild(settings_window);

// Toggle Preferred Links Section
preferredLinksHeader.onclick = function() {
    if (preferredLinksContent.style.display === "none") {
        preferredLinksContent.style.display = "block";
        toggleIcon.innerText = "⯅";  // Up arrow
    } else {
        preferredLinksContent.style.display = "none";
        toggleIcon.innerText = "⯆";  // Down arrow
    }
};

// Load preferred links when settings are opened
settingsIcon.onclick = function(event) {
    event.stopPropagation();

    const rect = settingsIcon.getBoundingClientRect();
    const settingsWindowY = rect.bottom + (isFixedMode ? 0 : window.scrollY)
    const settingsWindowX = rect.left + (isFixedMode ? 0 : window.scrollX)
    settings_window.style.top = `${settingsWindowY}px`;
    settings_window.style.left = `${settingsWindowX}px`;
    settings_window.style.display =
        settings_window.style.display === 'none' ? 'block' : 'none';
    settings_window.style.position = isFixedMode ? 'fixed' : 'absolute';

    // Load preferred links
    if (settings_window.style.display === 'block') {
        loadPreferredLinks();
    }
};

// Close settings popup when clicks outside
document.addEventListener('click', function(event) {
    const settingsWindow = document.getElementById('settings_window');
    if (
        settingsWindow.style.display === 'block' &&
        !settingsWindow.contains(event.target) &&
        !settingsIcon.contains(event.target) &&
        !positionModeIcon.contains(event.target)
    ) {
        settingsWindow.style.display = 'none';
    }
});

// Sources Window
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
sourcesCloseIcon.onclick = function() { sources_window.style.display = 'none'; };

sourcesHeader.appendChild(sourcesTitle);
sourcesHeader.appendChild(sourcesCloseIcon);

// Loading spinner
const loadingSpinner = document.createElement('div');
loadingSpinner.id = "loading_spinner";
loadingSpinner.className = "spinner";
loadingSpinner.style.display = 'none'; // Hide loading initially

const source_urls = document.createElement('ul');
source_urls.id = "source_urls";

sources_window.appendChild(sourcesHeader);
sources_window.appendChild(loadingSpinner);
sources_window.appendChild(source_urls);

// Append windows to the body
document.body.appendChild(sources_window);
document.body.appendChild(popup);

// Set initial positions for the main popup
popup.style.position = "absolute";
popup.style.top = "10%";
popup.style.left = "10%";
popup.style.width = '450px';
popup.style.height = '650px';

// Make popup draggable and resizable
let offsetX, offsetY, startX, startY, startWidth, startHeight;
let sourceWindowOffsetX = 10;
let isFixedMode = false; // fixedMode => stick to viewport (fixed positioning), otherwise stick to document (absolute positioning)

function makeDraggableAndResizable(element) {
    let isDragging = false;
    let isResizing = false;

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

// Initialize
makeDraggableAndResizable(popup);

const popupRect = popup.getBoundingClientRect();
sources_window.style.left = `${popupRect.right + sourceWindowOffsetX}px`;
sources_window.style.top = `${popupRect.top}px`;
