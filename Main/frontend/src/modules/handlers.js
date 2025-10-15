// handlers.js
import { appendChatElement } from './helpers.js';
import { getChatResponse, getChatResponseStream } from './api.js';
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
        // Remove "FinGPT: " prefix before copying
        const textToCopy = responseText.replace(/^FinGPT:\s*/, '');
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

        // Get current mode from DOM (don't use captured promptMode)
        const selectedModeElement = document.querySelector('.mode-option-selected');
        const currentMode = selectedModeElement ? selectedModeElement.dataset.mode : 'Normal';
        const currentPromptMode = currentMode === 'Extensive';

        // Resend the question with current settings
        handleChatResponse(userQuestion, currentPromptMode);
    };

    buttonContainer.appendChild(copyButton);
    buttonContainer.appendChild(retryButton);

    return buttonContainer;
}

// Function to create rating element
function createRatingElement() {
    const ratingContainer = document.createElement('div');
    ratingContainer.className = 'rating-container';

    const ratingStars = document.createElement('div');
    ratingStars.className = 'rating-stars';

    // Create 5 stars using UTF-8 characters
    const stars = [];
    for (let i = 0; i < 5; i++) {
        const star = document.createElement('span');
        star.className = 'rating-star';
        star.innerText = '★';
        star.dataset.rating = i + 1;
        stars.push(star);
        ratingStars.appendChild(star);
    }

    // Hover effect - fill stars up to the hovered star
    stars.forEach((star, index) => {
        star.addEventListener('mouseenter', () => {
            // Fill stars from 0 to current index
            for (let i = 0; i <= index; i++) {
                stars[i].classList.add('filled');
            }
            // Empty stars after current index
            for (let i = index + 1; i < stars.length; i++) {
                stars[i].classList.remove('filled');
            }
        });

        // Click handler - switch to thanks message
        star.addEventListener('click', () => {
            const rating = parseInt(star.dataset.rating);
            console.log(`User rated response: ${rating} stars`);

            // Clear container and show thanks message
            ratingContainer.innerHTML = '';
            const thanksText = document.createElement('span');
            thanksText.className = 'rating-thanks';
            thanksText.innerText = 'Thanks for the feedback!';
            ratingContainer.appendChild(thanksText);
        });
    });

    // Reset stars to empty when mouse leaves the stars container
    ratingStars.addEventListener('mouseleave', () => {
        stars.forEach(star => {
            star.classList.remove('filled');
        });
    });

    ratingContainer.appendChild(ratingStars);

    return ratingContainer;
}

// Function to handle chat responses (single model)
function handleChatResponse(question, promptMode = false, useStreaming = true) {
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

    // Check if streaming is available (not for MCP or RAG modes)
    const canStream = useStreaming && !useMCP && !useRAG;

    if (canStream) {
        // Use streaming response
        let isFirstChunk = true;

        getChatResponseStream(
            question,
            selectedModel,
            promptMode,
            useRAG,
            useMCP,
            // onChunk callback - called for each chunk of text
            (chunk, fullResponse) => {
                if (isFirstChunk) {
                    loadingElement.innerText = `FinGPT: ${fullResponse}`;
                    isFirstChunk = false;
                } else {
                    loadingElement.innerText = `FinGPT: ${fullResponse}`;
                }
                responseContainer.scrollTop = responseContainer.scrollHeight;
            },
            // onComplete callback - called when streaming is done
            (fullResponse, data) => {
                const endTime = performance.now();
                const responseTime = endTime - startTime;
                console.log(`Time taken for streaming response: ${responseTime} ms`);

                const responseText = `FinGPT: ${fullResponse}`;
                loadingElement.innerText = responseText;

                // Create action row containing both action buttons and rating
                const actionRow = document.createElement('div');
                actionRow.className = 'response-action-row';

                const actionButtons = createActionButtons(responseText, question, promptMode, useRAG, useMCP, selectedModel);
                const ratingElement = createRatingElement();

                actionRow.appendChild(actionButtons);
                actionRow.appendChild(ratingElement);
                responseContainer.appendChild(actionRow);

                // If this is research mode streaming and contains used_urls, cache them
                if (promptMode && data.used_urls && data.used_urls.length > 0) {
                    console.log('[Sources Debug] Research mode streaming response received');
                    console.log('[Sources Debug] used_urls:', data.used_urls);
                    console.log('[Sources Debug] Number of URLs:', data.used_urls.length);

                    setCachedSources(data.used_urls, question);
                    console.log('[Sources Debug] Cached', data.used_urls.length, 'source URLs from research mode streaming');
                }

                // Clear the user textbox
                document.getElementById('textbox').value = '';
                responseContainer.scrollTop = responseContainer.scrollHeight;
            },
            // onError callback
            (error) => {
                console.error('Streaming error:', error);
                loadingElement.innerText = `FinGPT: Failed to load response (streaming error).`;
            }
        );
    } else {
        // Use regular non-streaming response
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
                    responseText = `FinGPT: (No response from server)`;
                } else if (modelResponse.startsWith("The following file(s) are missing")) {
                    responseText = `FinGPT: Error - ${modelResponse}`;
                } else {
                    responseText = `FinGPT: ${modelResponse}`;
                }

                loadingElement.innerText = responseText;

                // Create action row containing both action buttons and rating
                const actionRow = document.createElement('div');
                actionRow.className = 'response-action-row';

                const actionButtons = createActionButtons(responseText, question, promptMode, useRAG, useMCP, selectedModel);
                const ratingElement = createRatingElement();

                actionRow.appendChild(actionButtons);
                actionRow.appendChild(ratingElement);
                responseContainer.appendChild(actionRow);

                // If this is an Advanced Ask response and contains used_urls, cache them
                if (promptMode && data.used_urls && data.used_urls.length > 0) {
                    console.log('[Sources Debug] Advanced Ask response received');
                    console.log('[Sources Debug] used_urls:', data.used_urls);
                    console.log('[Sources Debug] Number of URLs:', data.used_urls.length);

                    // Check each URL
                    data.used_urls.forEach((url, idx) => {
                        console.log(`[Sources Debug] URL ${idx + 1}: ${url}`);
                        if (url.includes('duckduckgo')) {
                            console.warn(`[Sources Debug] WARNING: DuckDuckGo URL found at index ${idx}: ${url}`);
                        }
                    });

                    setCachedSources(data.used_urls, question);
                    console.log('[Sources Debug] Cached', data.used_urls.length, 'source URLs from Advanced Ask');
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