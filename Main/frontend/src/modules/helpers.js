// helpers.js
import { clearMessages, getSourceUrls, logQuestion } from './api.js';
import { handleChatResponse, handleImageResponse } from './handlers.js';
import {
    clearCachedSources,
    getCurrentPageUrl,
    getCachedSourceEntries,
    getCurrentPageEntry,
    getLastSearchQuery,
    mergeCachedMetadata,
} from './sourcesCache.js';

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
    const searchQuery = getLastSearchQuery();
    const cachedOtherSources = getCachedSourceEntries(false);
    const cachedCurrentSource = getCurrentPageEntry();

    console.log('[Sources Debug] Loading sources for query:', searchQuery);
    console.log('[Sources Debug] Cached sources (excluding current page):', cachedOtherSources);

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

    const normalizeEntry = (entry) => {
        if (!entry || !entry.url) {
            return null;
        }
        const fallback = createFallbackMetadata(entry.url);
        if (!fallback) {
            return null;
        }
        const snippetSource = typeof entry.snippet === 'string' ? entry.snippet : fallback.snippet;
        const normalizedSnippet = snippetSource ? snippetSource.replace(/\s+/g, ' ').trim() : '';

        return {
            ...fallback,
            ...entry,
            site_name: entry.site_name || fallback.site_name,
            display_url: entry.display_url || fallback.display_url,
            title: entry.title || fallback.title,
            snippet: normalizedSnippet || fallback.snippet,
            image: entry.image !== undefined ? entry.image : fallback.image,
        };
    };

    const formatDisplayUrl = (url) => {
        if (!url) {
            return '';
        }

        const MAX_DISPLAY_URL_LENGTH = 30;
        let display = url;
        try {
            const parsed = new URL(url);
            display = `${parsed.hostname}${parsed.pathname}${parsed.search || ''}`;
        } catch (error) {
            // Leave display as url when it cannot be parsed
        }

        display = String(display).replace(/^www\./i, '');

        if (display.length > MAX_DISPLAY_URL_LENGTH) {
            const truncatedLength = Math.max(0, MAX_DISPLAY_URL_LENGTH - 3);
            display = `${display.slice(0, truncatedLength)}...`;
        }

        return display;
    };

    const createFallbackMetadata = (entry) => {
        if (!entry) {
            return null;
        }

        const url = typeof entry === 'string' ? entry : entry.url || '';
        if (!url) {
            return null;
        }

        const displayUrl = formatDisplayUrl(url);
        const siteName = getSiteNameFromUrl(url);
        const title = siteName || displayUrl;

        return {
            url,
            site_name: siteName,
            display_url: displayUrl,
            title,
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

        const headerWrapper = document.createElement('div');
        headerWrapper.className = 'source-card-header';

        const siteName = document.createElement('span');
        siteName.className = 'source-card-site';
        siteName.innerText = safeMeta.site_name || getSiteNameFromUrl(safeMeta.url);

        const displayUrl = document.createElement('span');
        displayUrl.className = 'source-card-url';
        const formattedDisplayUrl = formatDisplayUrl(safeMeta.url || safeMeta.display_url);
        displayUrl.innerText = formattedDisplayUrl;
        if (safeMeta.url || safeMeta.display_url) {
            displayUrl.title = safeMeta.url || safeMeta.display_url;
        }

        const metaWrapper = document.createElement('div');
        metaWrapper.className = 'source-card-meta';
        metaWrapper.appendChild(siteName);
        metaWrapper.appendChild(displayUrl);

        headerWrapper.appendChild(thumbnailWrapper);
        headerWrapper.appendChild(metaWrapper);

        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'source-card-content';

        const titleLink = document.createElement('span');
        titleLink.className = 'source-card-title';
        titleLink.innerText = safeMeta.title || siteName.innerText || displayUrl.innerText;

        const snippet = document.createElement('p');
        snippet.className = 'source-card-snippet';
        const snippetSource = typeof safeMeta.snippet === 'string' ? safeMeta.snippet : '';
        const snippetText = snippetSource.replace(/\s+/g, ' ').trim();
        snippet.innerText = snippetText ? snippetText : 'Preview unavailable.';

        contentWrapper.appendChild(titleLink);
        contentWrapper.appendChild(snippet);

        cardLink.appendChild(headerWrapper);
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

    let currentMetadata = cachedCurrentSource
        ? normalizeEntry(cachedCurrentSource)
        : (currentPageUrl ? createFallbackMetadata(currentPageUrl) : null);
    let sourcesToRender = cachedOtherSources.map((entry) => normalizeEntry(entry)).filter(Boolean);

    try {
        const response = await getSourceUrls(searchQuery || '', currentPageUrl);
        const payload = response?.resp || {};

        const backendSourcesRaw = Array.isArray(payload.sources) ? payload.sources : [];
        const backendCurrentRaw = payload.current_page && payload.current_page.url ? payload.current_page : null;

        mergeCachedMetadata([
            ...backendSourcesRaw,
            ...(backendCurrentRaw ? [backendCurrentRaw] : []),
        ]);

        if (backendCurrentRaw) {
            currentMetadata = normalizeEntry(backendCurrentRaw);
        } else if (currentPageUrl) {
            const refreshedCurrent = getCurrentPageEntry();
            if (refreshedCurrent) {
                currentMetadata = normalizeEntry(refreshedCurrent);
            }
        } else {
            currentMetadata = null;
        }

        const refreshedSources = getCachedSourceEntries(false).map((entry) => normalizeEntry(entry)).filter(Boolean);
        const backendFallback = backendSourcesRaw.map((entry) => normalizeEntry(entry)).filter(Boolean);

        if (refreshedSources.length > 0) {
            sourcesToRender = refreshedSources;
        } else if (backendFallback.length > 0) {
            sourcesToRender = backendFallback;
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
