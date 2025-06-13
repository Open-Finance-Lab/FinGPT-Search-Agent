// handlers.js
import { appendChatElement } from './helpers.js';
import { getChatResponse } from './api.js';
import { getSelectedModel, selectedModel } from './config.js';


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
        `FinGPT: Loading...`
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