// sourcesCache.js - Manages cached sources from Advanced Ask

let cachedSources = [];
let lastSearchQuery = '';

// Store sources from Advanced Ask response
function setCachedSources(urls, searchQuery = '') {
    cachedSources = urls || [];
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
    cachedSources = [];
    lastSearchQuery = '';
}

// Get last search query
function getLastSearchQuery() {
    return lastSearchQuery;
}

export {
    setCachedSources,
    getCachedSources,
    hasCachedSources,
    clearCachedSources,
    getLastSearchQuery
};