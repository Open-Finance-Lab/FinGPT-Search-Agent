// main.js
import { postWebTextToServer } from './modules/api.js';
import { createUI } from './modules/ui.js';

const currentUrl = window.location.href.toString();
console.log("Current page: ", currentUrl);

const textContent = document.body.innerText || "";
const encodedContent = encodeURIComponent(textContent);

// POST JSON to the server endpoint
postWebTextToServer(textContent, currentUrl)
    .then(data => {
        console.log("Response from server:", data);
    })
    .catch(error => {
        console.error("There was a problem with your fetch operation:", error);
    });

// Initialize UI
const { popup, settings_window, sources_window, searchQuery } = createUI();