// handlers.js
import { appendChatElement } from './helpers.js';
import { getChatResponse } from './api.js';
import { getSelectedModel, selectedModel } from './config.js';
import { setCachedSources } from './sourcesCache.js';

// Function to create action buttons (copy and retry)
function createActionButtons(responseText, userQuestion, promptMode, useRAG, useMCP, selectedModel) {
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'action-buttons';

    // Copy button
    const copyButton = document.createElement('button');
    copyButton.className = 'action-button copy-button';
    copyButton.title = 'Copy response';

    const copyIcon = document.createElement('img');
    copyIcon.src = chrome.runtime.getURL('assets/copy.png');
    copyIcon.alt = 'Copy';
    copyIcon.className = 'action-icon';
    copyButton.appendChild(copyIcon);

    copyButton.onclick = () => {
        // Remove "Search Agent: " prefix before copying
        const textToCopy = responseText.replace(/^Search Agent:\s*/, '');
        navigator.clipboard.writeText(textToCopy).then(() => {
            // Visual feedback
            copyButton.classList.add('action-button-clicked');
            setTimeout(() => {
                copyButton.classList.remove('action-button-clicked');
            }, 200);
        }).catch(err => {
            console.error('Failed to copy text:', err);
        });
    };

    // Retry button
    const retryButton = document.createElement('button');
    retryButton.className = 'action-button retry-button';
    retryButton.title = 'Retry';

    const retryIcon = document.createElement('img');
    retryIcon.src = chrome.runtime.getURL('assets/retry-1.png');
    retryIcon.alt = 'Retry';
    retryIcon.className = 'action-icon';
    retryButton.appendChild(retryIcon);

    retryButton.onclick = () => {
        // Visual feedback
        retryButton.classList.add('action-button-clicked');
        setTimeout(() => {
            retryButton.classList.remove('action-button-clicked');
        }, 200);

        // Resend the question
        handleChatResponse(userQuestion, promptMode);
    };

    buttonContainer.appendChild(copyButton);
    buttonContainer.appendChild(retryButton);

    return buttonContainer;
}

// Function to handle chat responses (single model)
function handleChatResponse(question, promptMode = false) {
    const startTime = performance.now();
    const responseContainer = document.getElementById('respons');

    // Show the user's question
    appendChatElement(responseContainer, 'your_question', question);

    // Placeholder "Loading..." text
    const loadingElement = appendChatElement(
        responseContainer,
        'agent_response',
        `Search Agent: Loading...`
    );

    // Read the RAG checkbox state
    const useRAG = document.getElementById('ragSwitch').checked;

    // Read the MCP mode toggle
    const useMCP = document.getElementById('mcpModeSwitch').checked;

    const selectedModel = getSelectedModel();

    getChatResponse(question, selectedModel, promptMode, useRAG, useMCP)
        .then(data => {
            const endTime = performance.now();
            const responseTime = endTime - startTime;
            console.log(`Time taken for response: ${responseTime} ms`);

            // Extract the reply: MCP gives `data.reply`, normal gives `data.resp[...]`
            const modelResponse = useMCP ? data.reply : data.resp[selectedModel];

            let responseText = '';
            if (!modelResponse) {
                // Safeguard in case backend does not return something
                responseText = `Search Agent: (No response from server)`;
            } else if (modelResponse.startsWith("The following file(s) are missing")) {
                responseText = `Search Agent: Error - ${modelResponse}`;
            } else {
                responseText = `Search Agent: ${modelResponse}`;
            }

            loadingElement.innerText = responseText;

            // Add action buttons after the response
            const actionButtons = createActionButtons(responseText, question, promptMode, useRAG, useMCP, selectedModel);
            responseContainer.appendChild(actionButtons);

            // If this is an Advanced Ask response and contains used_urls, cache them
            if (promptMode && data.used_urls && data.used_urls.length > 0) {
                setCachedSources(data.used_urls, question);
                console.log('Cached', data.used_urls.length, 'source URLs from Advanced Ask');
            }

            // Clear the user textbox
            document.getElementById('textbox').value = '';
            responseContainer.scrollTop = responseContainer.scrollHeight;
        })
        .catch(error => {
            console.error('There was a problem with your fetch operation:', error);
            loadingElement.innerText = `Search Agent: Failed to load response.`;
        });
}

// Function to handle image response
function handleImageResponse(question, description) {
    const responseContainer = document.getElementById('respons');
    appendChatElement(responseContainer, 'your_question', question);

    const responseDiv = document.createElement('div');
    responseDiv.className = 'agent_response';
    responseDiv.innerText = description;
    responseContainer.appendChild(responseDiv);

    responseContainer.scrollTop = responseContainer.scrollHeight;
}

export { handleChatResponse, handleImageResponse };