// sourcesCache.js - Manages cached sources from Advanced Ask

let cachedSources = [];
let lastSearchQuery = '';
let currentPageUrl = '';

// Initialize with current page URL
function initializeWithCurrentPage(url) {
    currentPageUrl = url;
    // Ensure current page is always in the cache
    if (!cachedSources.includes(url)) {
        cachedSources = [url, ...cachedSources];
    }
    console.log('Initialized with current page:', url);
}

// Store sources from Advanced Ask response
function setCachedSources(urls, searchQuery = '') {
    console.log('[Sources Debug] setCachedSources called');
    console.log('[Sources Debug] Input URLs:', urls);
    console.log('[Sources Debug] Current page URL:', currentPageUrl);

    const newUrls = urls || [];

    // Filter out current page URL from newUrls if it exists
    const filteredUrls = newUrls.filter(url => url !== currentPageUrl);

    // Always keep current page URL at the beginning
    if (currentPageUrl) {
        cachedSources = [currentPageUrl, ...filteredUrls];
    } else {
        cachedSources = filteredUrls;
    }
    lastSearchQuery = searchQuery;

    console.log('[Sources Debug] Final cached sources:', cachedSources);
    console.log('[Sources Debug] Total cached:', cachedSources.length, 'URLs');

    // Check for any DuckDuckGo URLs
    cachedSources.forEach((url, idx) => {
        if (url.includes('duckduckgo')) {
            console.warn(`[Sources Debug] WARNING: DuckDuckGo URL cached at index ${idx}: ${url}`);
        }
    });
}

// Get cached sources
function getCachedSources() {
    return cachedSources;
}

// Check if we have cached sources
function hasCachedSources() {
    return cachedSources.length > 0;
}

// Clear cached sources
function clearCachedSources() {
    // Keep current page URL when clearing
    if (currentPageUrl) {
        cachedSources = [currentPageUrl];
    } else {
        cachedSources = [];
    }
    lastSearchQuery = '';
}

// Get last search query
function getLastSearchQuery() {
    return lastSearchQuery;
}

// Get current page URL
function getCurrentPageUrl() {
    return currentPageUrl;
}

// Get cached sources without current page URL
function getCachedSourcesWithoutCurrentPage() {
    return cachedSources.filter(url => url !== currentPageUrl);
}

export {
    initializeWithCurrentPage,
    setCachedSources,
    getCachedSources,
    hasCachedSources,
    clearCachedSources,
    getLastSearchQuery,
    getCurrentPageUrl,
    getCachedSourcesWithoutCurrentPage
};