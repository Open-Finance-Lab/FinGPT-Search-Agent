// main.js
import { postWebTextToServer, setSessionId } from './modules/api.js';
import { createUI } from './modules/ui.js';
import { fetchAvailableModels } from './modules/config.js';
import { initializeWithCurrentPage } from './modules/sourcesCache.js';
import { getBackendBaseUrl } from './modules/backendConfig.js';

// Generate a unique session ID for this page load
const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
setSessionId(sessionId);
console.log("Agentic FinSearch Session ID: ", sessionId);

const currentUrl = window.location.href.toString();
console.log("Current page: ", currentUrl);

// Initialize sources cache with current page URL
initializeWithCurrentPage(currentUrl);

// Legacy JS scraping DISABLED - Using Playwright MCP only
// const textContent = document.body.innerText || "";
// const encodedContent = encodeURIComponent(textContent);

// Fetch available models from backend on startup
fetchAvailableModels().then(() => {
    console.log("Models fetched from backend");
}).catch(error => {
    console.error("CRITICAL: Failed to fetch models from backend:", error);
    alert(`Failed to connect to Agentic FinSearch backend: ${error.message}\n\nPlease ensure the backend server at ${getBackendBaseUrl()} is reachable.`);
});

// Legacy JS scraping DISABLED to verify Playwright MCP functionality
// The agent will now ONLY use Playwright MCP tools to scrape webpages
console.log("[MCP MODE] Legacy JS scraping disabled - agent will use Playwright MCP for page content");

// POST JSON to the server endpoint
// postWebTextToServer(textContent, currentUrl)
//     .then(data => {
//         console.log("Response from server:", data);
//     })
//     .catch(error => {
//         console.error("There was a problem with your fetch operation:", error);
//     });

// Initialize UI
const { popup, settings_window, sources_window, searchQuery } = createUI();
