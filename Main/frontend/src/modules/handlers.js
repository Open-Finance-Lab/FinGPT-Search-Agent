// handlers.js
import { appendChatElement } from './helpers.js';
import { getChatResponse } from './api.js';
import { getSelectedModel, selectedModel } from './config.js';
import { setCachedSources } from './sourcesCache.js';


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

            if (!modelResponse) {
                // Safeguard in case backend does not return something
                loadingElement.innerText = `Search Agent: (No response from server)`;
            } else if (modelResponse.startsWith("The following file(s) are missing")) {
                loadingElement.innerText = `Search Agent: Error - ${modelResponse}`;
            } else {
                loadingElement.innerText = `Search Agent: ${modelResponse}`;
            }

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