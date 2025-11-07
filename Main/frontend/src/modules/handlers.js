// handlers.js
import { appendChatElement, scrollChatToBottom } from './helpers.js';
import { getChatResponse, getChatResponseStream } from './api.js';
import { getSelectedModel, selectedModel } from './config.js';
import { setCachedSources } from './sourcesCache.js';
import { marked } from 'marked';
import renderMathInElement from 'katex/dist/contrib/auto-render';

function renderMarkdown(text) {
  return marked.parse(text, {
    gfm: true,
    breaks: true,
    mangle: false,
    headerIds: false,
  });
}

function renderMarkdownWithMath(element, text) {
  const mathBlocks = [];

  // Extract all math blocks to protect them from markdown processing
  // Order matters: extract display math before inline math to avoid conflicts

  // Extract \[ ... \] (LaTeX display math)
  let processedText = text.replace(/\\\[([\s\S]+?)\\\]/g, (match) => {
    const index = mathBlocks.length;
    mathBlocks.push(match);
    return `XMATHXBLOCKX${index}XENDX`;
  });

  // Extract $$ ... $$ (display math)
  processedText = processedText.replace(/\$\$([\s\S]+?)\$\$/g, (match) => {
    const index = mathBlocks.length;
    mathBlocks.push(match);
    return `XMATHXBLOCKX${index}XENDX`;
  });

  // Extract \( ... \) (LaTeX inline math)
  processedText = processedText.replace(/\\\(([\s\S]+?)\\\)/g, (match) => {
    const index = mathBlocks.length;
    mathBlocks.push(match);
    return `XMATHXBLOCKX${index}XENDX`;
  });

  // Extract $ ... $ (inline math)
  processedText = processedText.replace(/\$([^\$\n]+?)\$/g, (match) => {
    const index = mathBlocks.length;
    mathBlocks.push(match);
    return `XMATHXBLOCKX${index}XENDX`;
  });

  // Render markdown
  let html = renderMarkdown(processedText);

  // Restore all math blocks
  mathBlocks.forEach((block, index) => {
    const escapedPlaceholder = `XMATHXBLOCKX${index}XENDX`;
    html = html.replace(new RegExp(escapedPlaceholder, 'g'), block);
  });

  element.innerHTML = `<strong>FinGPT:</strong> ${html}`;

  const links = element.querySelectorAll('a');
  links.forEach((link) => {
    link.setAttribute('target', '_blank');
    link.setAttribute('rel', 'noopener noreferrer');
  });

  // Let KaTeX handle all the math rendering
  renderMathInElement(element, {
    delimiters: [
      { left: '$$', right: '$$', display: true },
      { left: '$', right: '$', display: false },
      { left: '\\[', right: '\\]', display: true },
      { left: '\\(', right: '\\)', display: false },
    ],
    throwOnError: false,
    errorColor: '#cc0000',
    strict: false,
    trust: true,
  });
}

function createLoadingCard(responseContainer) {
  const card = document.createElement('div');
  card.className = 'agent_response agent-loading-card';

  const title = document.createElement('div');
  title.className = 'loading-card-title';
  title.innerText = 'FinGPT is working';

  const currentWrapper = document.createElement('div');
  currentWrapper.className = 'loading-card-current';

  const currentLabel = document.createElement('div');
  currentLabel.className = 'loading-card-current-label';
  currentWrapper.appendChild(currentLabel);

  const currentDetail = document.createElement('div');
  currentDetail.className = 'loading-card-current-detail';
  currentWrapper.appendChild(currentDetail);

  const historyList = document.createElement('ul');
  historyList.className = 'loading-card-history';

  card.appendChild(title);
  card.appendChild(currentWrapper);
  card.appendChild(historyList);
  responseContainer.appendChild(card);

  const MAX_HISTORY = 4;
  let currentStatus = null;
  let isActive = true;

  const normalize = (status = {}) => ({
    label: status.label || '',
    detail: status.detail || '',
    url: status.url || '',
  });

  const appendHistory = (status) => {
    if (!status || !status.label) {
      return;
    }
    const item = document.createElement('li');
    item.className = 'loading-card-history-item';

    const labelSpan = document.createElement('span');
    labelSpan.className = 'history-label';
    labelSpan.innerText = status.label;
    item.appendChild(labelSpan);

    if (status.detail) {
      const detailSpan = document.createElement('span');
      detailSpan.className = 'history-detail';
      detailSpan.innerText = status.detail;
      item.appendChild(detailSpan);
    }

    historyList.insertBefore(item, historyList.firstChild);
    while (historyList.children.length > MAX_HISTORY) {
      historyList.removeChild(historyList.lastChild);
    }
  };

  const updateStatus = (status) => {
    if (!isActive) {
      return;
    }
    const next = normalize(status);
    if (!next.label) {
      return;
    }
    if (
      currentStatus &&
      currentStatus.label === next.label &&
      currentStatus.detail === next.detail
    ) {
      return;
    }
    if (currentStatus) {
      appendHistory(currentStatus);
    }
    currentStatus = next;
    currentLabel.innerText = next.label;
    if (next.detail) {
      currentDetail.innerText = next.detail;
      currentDetail.style.display = 'block';
    } else {
      currentDetail.innerText = '';
      currentDetail.style.display = 'none';
    }
  };

  const complete = () => {
    if (!isActive) {
      return;
    }
    currentStatus = null;
    isActive = false;
    if (card.parentNode) {
      card.parentNode.removeChild(card);
    }
  };

  const fail = (message) => {
    if (!isActive) {
      return;
    }
    card.classList.add('agent-loading-card--error');
    currentLabel.innerText = 'Issue detected';
    currentDetail.innerText = message || 'Unable to finish this request.';
    currentDetail.style.display = 'block';
    historyList.innerHTML = '';
  };

  return {
    element: card,
    updateStatus,
    complete,
    fail,
  };
}

// Function to create action buttons (copy and retry)
function createActionButtons(
  responseText,
  userQuestion,
  promptMode,
  useRAG,
  useMCP,
  selectedModel
) {
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
    navigator.clipboard
      .writeText(textToCopy)
      .then(() => {
        // Visual feedback
        copyButton.classList.add('action-button-clicked');
        setTimeout(() => {
          copyButton.classList.remove('action-button-clicked');
        }, 200);
      })
      .catch((err) => {
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
    const currentMode = selectedModeElement
      ? selectedModeElement.dataset.mode
      : 'Normal';
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
    stars.forEach((star) => {
      star.classList.remove('filled');
    });
  });

  ratingContainer.appendChild(ratingStars);

  return ratingContainer;
}

// Apply Markdown and LaTeX rendering to an existing message bubble
function renderFormattedResponse(targetElement, rawText) {
    if (!targetElement) {
        return;
    }

    const formattedText = formatMathExpressions(rawText);
    const markdownHtml = marked.parse(formattedText, {
        gfm: true,
        breaks: true,
        mangle: false,
        headerIds: false,
    });

    targetElement.innerHTML = markdownHtml;

    renderMathInElement(targetElement, {
        delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$', right: '$', display: false },
            { left: '\\(', right: '\\)', display: false },
            { left: '\\[', right: '\\]', display: true },
        ],
        output: 'html',
        throwOnError: false,
        errorColor: '#cc0000',
        macros: {
            '\\Δ': '\\Delta',
            '\\σ': '\\sigma',
            '\\ν': '\\nu',
            '\\ρ': '\\rho',
            '\\Γ': '\\Gamma',
            '\\Θ': '\\theta',
        },
        trust: true,
        strict: false,
    });
}

// Lightly adapted from popup.js to wrap math expressions with delimiters
function formatMathExpressions(text) {
    if (!text) {
        return text;
    }

    let processed = text.replace(/(?<!\$)([^\s$])([^$\n]+?)(?<!\$)([^\s$])/g, (match, p1, p2, p3) => {
        if (/[∂σ²∆ΓΘνρ√]|\b[dN]_[12]\b|\bln\b|\be\^/.test(match)) {
            return `${p1}$${p2}${p3}$`;
        }
        return match;
    });

    processed = processed.replace(/^\s*([^$\n]+?)\s*$/gm, (match) => {
        if (/[∂σ²∆ΓΘνρ√=−].*[∂σ²∆ΓΘνρ√=−]/.test(match) && !/\$\$.*\$\$/.test(match)) {
            return `$$${match}$$`;
        }
        return match;
    });

    return processed;
}

// Function to handle chat responses (single model)
function handleChatResponse(question, promptMode = false, useStreaming = true) {
  const startTime = performance.now();
  const responseContainer = document.getElementById('respons');

  // Show the user's question
  appendChatElement(responseContainer, 'your_question', question);

  // Scroll to show the new question immediately
  scrollChatToBottom();

  const loadingCard = createLoadingCard(responseContainer);
  loadingCard.updateStatus({
    label: 'Preparing context',
    detail: promptMode ? 'Research mode' : 'Thinking mode',
  });

  const responseElement = appendChatElement(responseContainer, 'agent_response', '');
  responseElement.style.display = 'none';

  // Read the RAG checkbox state
  const ragSwitchEl = document.getElementById('ragSwitch');
  const useRAG = ragSwitchEl ? !!ragSwitchEl.checked : false;

  // Read the MCP mode toggle
  const mcpSwitchEl = document.getElementById('mcpModeSwitch');
  const useMCP = mcpSwitchEl ? !!mcpSwitchEl.checked : false;

  const selectedModel = getSelectedModel();

  // Check if streaming is available (not for MCP or RAG modes)
  const canStream = useStreaming && !useMCP && !useRAG;
  if (!canStream) {
    loadingCard.updateStatus({
      label: 'Processing request',
      detail: useMCP ? 'MCP mode' : useRAG ? 'RAG mode' : 'Standard pipeline',
    });
  }

  if (canStream) {
    // Use streaming response
    let isFirstChunk = true;
    let loadingDismissed = false;
    const dismissLoading = () => {
      if (!loadingDismissed) {
        loadingDismissed = true;
        loadingCard.complete();
      }
    };

    getChatResponseStream(
      question,
      selectedModel,
      promptMode,
      useRAG,
      useMCP,
      {
        // onChunk callback - called for each chunk of text
        onChunk: (chunk, fullResponse) => {
          if (isFirstChunk) {
            isFirstChunk = false;
            dismissLoading();
          }
          if (responseElement.style.display === 'none') {
            responseElement.style.display = 'block';
          }
          renderMarkdownWithMath(responseElement, fullResponse);
          scrollChatToBottom();
        },
        // onComplete callback - called when streaming is done
        onComplete: (fullResponse, data) => {
          const endTime = performance.now();
          const responseTime = endTime - startTime;
          console.log(`Time taken for streaming response: ${responseTime} ms`);
          console.log('[Debug] onComplete data:', data);
          console.log('[Debug] promptMode:', promptMode);

          const responseText = `FinGPT: ${fullResponse}`;
          if (responseElement.style.display === 'none') {
            responseElement.style.display = 'block';
          }
          renderMarkdownWithMath(responseElement, fullResponse);

          // Create action row containing both action buttons and rating
          const actionRow = document.createElement('div');
          actionRow.className = 'response-action-row';

          const actionButtons = createActionButtons(
            responseText,
            question,
            promptMode,
            useRAG,
            useMCP,
            selectedModel
          );
          const ratingElement = createRatingElement();

          actionRow.appendChild(actionButtons);
          actionRow.appendChild(ratingElement);
          responseContainer.appendChild(actionRow);

          // If this is research mode streaming and contains used_urls, cache them
          if (promptMode) {
            console.log(
              '[Sources Debug] Research mode streaming - checking for URLs'
            );
            console.log(
              '[Sources Debug] data.used_urls exists?',
              !!data.used_urls
            );
            console.log(
              '[Sources Debug] data.used_urls is array?',
              Array.isArray(data.used_urls)
            );
            console.log(
              '[Sources Debug] data.used_urls length:',
              data.used_urls?.length
            );
            console.log(
              '[Sources Debug] data.used_sources exists?',
              !!data.used_sources
            );

            if (data.used_urls && data.used_urls.length > 0) {
              console.log(
                '[Sources Debug] Research mode streaming response received'
              );
              console.log('[Sources Debug] used_urls:', data.used_urls);
              console.log(
                '[Sources Debug] Number of URLs:',
                data.used_urls.length
              );

              const metadata = Array.isArray(data.used_sources)
                ? data.used_sources
                : [];
              setCachedSources(data.used_urls, question, metadata);
              console.log(
                '[Sources Debug] Called setCachedSources with',
                data.used_urls.length,
                'URLs and',
                metadata.length,
                'metadata entries'
              );
              console.log(
                '[Sources Debug] Sources should now be cached for query:',
                question
              );
            } else {
              console.warn(
                '[Sources Debug] Research mode but NO URLs found in response!'
              );
            }
          } else {
            console.log(
              '[Sources Debug] Not in promptMode, skipping source caching'
            );
          }

          // Clear the user textbox
          document.getElementById('textbox').value = '';
          scrollChatToBottom();
          dismissLoading();
        },
        // onError callback
        onError: (error) => {
          console.error('Streaming error:', error);
          responseElement.style.display = 'block';
          responseElement.innerHTML = `<strong>FinGPT:</strong> Failed to load response (streaming error).`;
          loadingCard.fail('Streaming error');
        },
        onStatus: (status) => {
          loadingCard.updateStatus(status);
        },
      }
    );
  } else {
    // Use regular non-streaming response
    getChatResponse(question, selectedModel, promptMode, useRAG, useMCP)
      .then((data) => {
        const endTime = performance.now();
        const responseTime = endTime - startTime;
        console.log(`Time taken for response: ${responseTime} ms`);

        // Extract the reply: MCP gives `data.reply`, normal gives `data.resp[...]`
        const modelResponse = useMCP ? data.reply : data.resp[selectedModel];

        let responseText = '';
        if (!modelResponse) {
          // Safeguard in case backend does not return something
          responseText = `FinGPT: (No response from server)`;
        } else if (
          modelResponse.startsWith('The following file(s) are missing')
        ) {
          responseText = `FinGPT: Error - ${modelResponse}`;
        } else {
          responseText = `FinGPT: ${modelResponse}`;
        }

        responseElement.style.display = 'block';
        renderMarkdownWithMath(responseElement, modelResponse);

        // Create action row containing both action buttons and rating
        const actionRow = document.createElement('div');
        actionRow.className = 'response-action-row';

        const actionButtons = createActionButtons(
          responseText,
          question,
          promptMode,
          useRAG,
          useMCP,
          selectedModel
        );
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
              console.warn(
                `[Sources Debug] WARNING: DuckDuckGo URL found at index ${idx}: ${url}`
              );
            }
          });

          const metadata = Array.isArray(data.used_sources)
            ? data.used_sources
            : [];
          setCachedSources(data.used_urls, question, metadata);
          console.log(
          '[Sources Debug] Cached',
          data.used_urls.length,
          'source URLs from Advanced Ask'
        );
        }

        // Clear the user textbox
        document.getElementById('textbox').value = '';
        scrollChatToBottom();
        loadingCard.complete();
      })
      .catch((error) => {
        console.error('There was a problem with your fetch operation:', error);
        responseElement.style.display = 'block';
        responseElement.innerHTML = `<strong>FinGPT:</strong> Failed to load response.`;
        loadingCard.fail('Network error');
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

  scrollChatToBottom();
}

export { handleChatResponse, handleImageResponse };
