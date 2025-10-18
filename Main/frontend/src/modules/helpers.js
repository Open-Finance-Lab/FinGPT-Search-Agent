// helpers.js
import { clearMessages, getSourceUrls, logQuestion } from './api.js';
import { handleChatResponse, handleImageResponse } from './handlers.js';
import { clearCachedSources, getCurrentPageUrl, getCachedSourcesWithoutCurrentPage, getLastSearchQuery } from './sourcesCache.js';

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

// Unified submit function for the new mode selector
function submit_question(mode) {
    const question = document.getElementById('textbox').value.trim();

    if (question === '') {
        alert("Please enter a message.");
        return;
    }

    if (mode === 'Thinking') {
        // Thinking mode - equivalent to old "Ask" button
        handleChatResponse(question, false);
        logQuestion(question, 'Thinking');
    } else if (mode === 'Research') {
        // Research mode - equivalent to old "Advanced Ask" button
        // Clear previous cached sources before making new advanced request
        clearCachedSources();
        handleChatResponse(question, true);
        logQuestion(question, 'Research');
    }

    document.getElementById('textbox').value = '';
}

// Function to get sources
async function get_sources() {
    const sources_window = document.getElementById('sources_window');
    const loadingSpinner = document.getElementById('loading_spinner');
    const sourceContainer = document.getElementById('source_urls');

    sources_window.style.display = 'block';
    loadingSpinner.style.display = 'block';
    sourceContainer.style.display = 'none';
    sourceContainer.innerHTML = '';

    const currentPageUrl = getCurrentPageUrl();
    const otherSources = getCachedSourcesWithoutCurrentPage();
    const searchQuery = getLastSearchQuery();

    console.log('[Sources Debug] Loading sources for query:', searchQuery);
    console.log('[Sources Debug] Cached sources (excluding current page):', otherSources);

    const neutralDomainParts = ['co', 'com', 'org', 'net', 'gov', 'edu'];

    const toTitleCase = (value) => value.replace(/\b\w/g, (letter) => letter.toUpperCase());

    const getSiteNameFromUrl = (url) => {
        try {
            const { hostname } = new URL(url);
            const trimmed = hostname.replace(/^www\./i, '');
            const parts = trimmed.split('.');
            let candidate = parts.length >= 2 ? parts[parts.length - 2] : parts[0];
            if (neutralDomainParts.includes(candidate) && parts.length >= 3) {
                candidate = parts[parts.length - 3];
            }
            const cleaned = candidate.replace(/[-_]/g, ' ').trim();
            return cleaned ? toTitleCase(cleaned) : trimmed;
        } catch (error) {
            return 'Source';
        }
    };

    const formatDisplayUrl = (url) => {
        if (!url) {
            return '';
        }
        try {
            const parsed = new URL(url);
            let display = `${parsed.hostname}${parsed.pathname}`;
            if (parsed.search) {
                display += parsed.search;
            }
            display = display.replace(/^www\./i, '');
            if (display.length > 80) {
                display = `${display.slice(0, 77)}...`;
            }
            return display || url;
        } catch (error) {
            return url;
        }
    };

    const createFallbackMetadata = (url) => {
        if (!url) {
            return null;
        }
        const displayUrl = formatDisplayUrl(url);
        return {
            url,
            site_name: getSiteNameFromUrl(url),
            display_url: displayUrl,
            title: displayUrl,
            snippet: null,
            image: null,
        };
    };

    const buildThumbnail = (wrapper, metadata) => {
        const fallbackInitial = (metadata.site_name || metadata.display_url || '?').charAt(0).toUpperCase();

        const applyFallback = () => {
            wrapper.innerHTML = '';
            wrapper.classList.add('source-card-thumbnail--fallback');
            wrapper.textContent = fallbackInitial || '?';
        };

        if (metadata.image) {
            const img = document.createElement('img');
            img.src = metadata.image;
            img.alt = metadata.title || metadata.display_url || 'Source preview';
            img.loading = 'lazy';
            img.onerror = applyFallback;
            wrapper.appendChild(img);
        } else {
            applyFallback();
        }
    };

    const buildSourceCard = (metadata) => {
        const safeMeta = metadata || {};
        if (!safeMeta.url) {
            return null;
        }

        const cardLink = document.createElement('a');
        cardLink.className = 'source-card';
        cardLink.href = safeMeta.url;
        cardLink.target = '_blank';
        cardLink.rel = 'noopener noreferrer';

        const thumbnailWrapper = document.createElement('div');
        thumbnailWrapper.className = 'source-card-thumbnail';
        buildThumbnail(thumbnailWrapper, safeMeta);

        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'source-card-content';

        const metaWrapper = document.createElement('div');
        metaWrapper.className = 'source-card-meta';

        const siteName = document.createElement('span');
        siteName.className = 'source-card-site';
        siteName.innerText = safeMeta.site_name || getSiteNameFromUrl(safeMeta.url);

        const displayUrl = document.createElement('span');
        displayUrl.className = 'source-card-url';
        displayUrl.innerText = safeMeta.display_url || formatDisplayUrl(safeMeta.url);

        metaWrapper.appendChild(siteName);
        metaWrapper.appendChild(displayUrl);

        const titleLink = document.createElement('span');
        titleLink.className = 'source-card-title';
        titleLink.innerText = safeMeta.title || siteName.innerText || displayUrl.innerText;

        const snippet = document.createElement('p');
        snippet.className = 'source-card-snippet';
        const snippetSource = typeof safeMeta.snippet === 'string' ? safeMeta.snippet : '';
        const snippetText = snippetSource.replace(/\s+/g, ' ').trim();
        snippet.innerText = snippetText ? snippetText : 'Preview unavailable.';

        contentWrapper.appendChild(metaWrapper);
        contentWrapper.appendChild(titleLink);
        contentWrapper.appendChild(snippet);

        cardLink.appendChild(thumbnailWrapper);
        cardLink.appendChild(contentWrapper);
        cardLink.setAttribute('aria-label', `${siteName.innerText}: ${titleLink.innerText}`);
        return cardLink;
    };

    const appendSection = (title, items, emptyMessage) => {
        const section = document.createElement('div');
        section.className = 'source-section';

        const header = document.createElement('div');
        header.className = 'source-section-header';
        header.innerText = title;
        section.appendChild(header);

        const content = document.createElement('div');
        content.className = 'source-section-content';

        if (items.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'empty-sources';
            empty.innerText = emptyMessage;
            content.appendChild(empty);
        } else {
            items.forEach((metadata) => {
                const card = buildSourceCard(metadata);
                if (card) {
                    content.appendChild(card);
                }
            });
        }

        section.appendChild(content);
        sourceContainer.appendChild(section);
    };

    let currentMetadata = currentPageUrl ? createFallbackMetadata(currentPageUrl) : null;
    let sourcesToRender = otherSources.map((url) => createFallbackMetadata(url)).filter(Boolean);

    try {
        const response = await getSourceUrls(searchQuery || '', currentPageUrl);
        const payload = response?.resp || {};
        const metadataMap = new Map();

        if (Array.isArray(payload.sources)) {
            payload.sources.forEach((entry) => {
                if (entry && entry.url) {
                    metadataMap.set(entry.url, entry);
                }
            });
        }

        if (payload.current_page && payload.current_page.url) {
            currentMetadata = payload.current_page;
        } else if (currentPageUrl && metadataMap.has(currentPageUrl)) {
            currentMetadata = metadataMap.get(currentPageUrl);
        } else if (!currentPageUrl) {
            currentMetadata = null;
        }

        const seen = new Set();
        sourcesToRender = [];

        if (otherSources.length > 0) {
            otherSources.forEach((url) => {
                if (!url || seen.has(url)) {
                    return;
                }
                const metadata = metadataMap.get(url) || createFallbackMetadata(url);
                if (metadata) {
                    sourcesToRender.push(metadata);
                    seen.add(url);
                }
            });
        }

        if (sourcesToRender.length === 0 && Array.isArray(payload.sources)) {
            payload.sources.forEach((entry) => {
                if (!entry || !entry.url || seen.has(entry.url)) {
                    return;
                }
                sourcesToRender.push(entry);
                seen.add(entry.url);
            });
        }
    } catch (error) {
        console.error('Unable to load source previews:', error);
    } finally {
        loadingSpinner.style.display = 'none';
        sourceContainer.style.display = 'flex';
    }

    appendSection(
        'Current active webpage',
        currentMetadata ? [currentMetadata] : [],
        'No current webpage detected'
    );

    appendSection(
        'Sources used',
        sourcesToRender,
        'Sources used for agent responses when using Research mode will appear here.'
    );
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

        // Move sources window with main popup (now on the left side)
        const sourcesWindow = document.getElementById('sources_window');
        if (sourcesWindow) {
            const measuredWidth = sourcesWindow.offsetWidth || 360;
            const sourcesLeft = Math.max(0, newX - (measuredWidth + sourceWindowOffsetX));
            sourcesWindow.style.left = `${sourcesLeft}px`;
            sourcesWindow.style.top = `${newY}px`;
        }
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

        const sourcesWindow = document.getElementById('sources_window');
        if (sourcesWindow) {
            const measuredWidth = sourcesWindow.offsetWidth || 360;
            const sourcesLeft = Math.max(0, element.offsetLeft - (measuredWidth + sourceWindowOffsetX));
            sourcesWindow.style.left = `${sourcesLeft}px`;
        }
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
