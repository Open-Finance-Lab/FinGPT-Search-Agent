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
    const newUrls = urls || [];
    // Always keep current page URL at the beginning
    if (currentPageUrl && !newUrls.includes(currentPageUrl)) {
        cachedSources = [currentPageUrl, ...newUrls];
    } else {
        cachedSources = newUrls;
    }
    lastSearchQuery = searchQuery;
    console.log('Sources cached:', cachedSources.length, 'URLs');
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

export {
    initializeWithCurrentPage,
    setCachedSources,
    getCachedSources,
    hasCachedSources,
    clearCachedSources,
    getLastSearchQuery
};