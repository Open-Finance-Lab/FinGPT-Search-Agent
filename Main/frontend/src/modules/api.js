// api.js

// Session ID management
let currentSessionId = null;

function setSessionId(sessionId) {
    currentSessionId = sessionId;
}

// Function to POST JSON to the server endpoint
function postWebTextToServer(textContent, currentUrl) {
    return fetch("http://127.0.0.1:8000/input_webtext/", {
        method: "POST",
        credentials: "include",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            textContent: textContent,
            currentUrl: currentUrl,
            use_r2c: true,
            session_id: currentSessionId
        }),
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok (status: ${response.status})`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Response from server:", data);
            return data;
        })
        .catch(error => {
            console.error("There was a problem with your fetch operation:", error);
            throw error;
        });
}

// Function to get chat response from server (now supports MCP mode)
function getChatResponse(question, selectedModel, promptMode, useRAG, useMCP) {
    const encodedQuestion = encodeURIComponent(question);

    let endpoint;
    if (useMCP) {
      endpoint = 'get_mcp_response';
    } else {
      endpoint = promptMode ? 'get_adv_response' : 'get_chat_response';
    }

    // Get preferred links from localStorage for advanced mode
    let url = `http://127.0.0.1:8000/${endpoint}/?question=${encodedQuestion}` +
        `&models=${selectedModel}` +
        `&is_advanced=${promptMode}` +
        `&use_rag=${useRAG}` +
        `&use_r2c=true` +
        `&session_id=${currentSessionId}`;

    // Add preferred links if in advanced mode
    if (promptMode) {
        try {
            const preferredLinks = JSON.parse(localStorage.getItem('preferredLinks') || '[]');
            if (preferredLinks.length > 0) {
                url += `&preferred_links=${encodeURIComponent(JSON.stringify(preferredLinks))}`;
            }
        } catch (e) {
            console.error('Error getting preferred links:', e);
        }
    }

    return fetch(url, { method: 'GET', credentials: 'include' })
        .then(response => response.json())
        .catch(error => {
            console.error('There was a problem with your fetch operation:', error);
            throw error;
        });
}

// Function to clear messages
function clearMessages() {
    return fetch(`http://127.0.0.1:8000/clear_messages/?use_r2c=true&session_id=${currentSessionId}`, { method: "POST", credentials: "include" })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .catch(error => {
            console.error('There was a problem with your fetch operation:', error);
            throw error;
        });
}

// Function to get sources
function getSourceUrls(searchQuery) {
    return fetch(`http://127.0.0.1:8000/get_source_urls/?query=${String(searchQuery)}`, { method: "GET", credentials: "include" })
        .then(response => response.json())
        .catch(error => {
            console.error('There was a problem with your fetch operation:', error);
            throw error;
        });
}

// Function to log question
function logQuestion(question, button) {
    const currentUrl = window.location.href;

    return fetch(
        `http://127.0.0.1:8000/log_question/?question=${encodeURIComponent(question)}&button=${encodeURIComponent(button)}&current_url=${encodeURIComponent(currentUrl)}`,
        { method: "GET", credentials: "include" }
    )
        .then(response => response.json())
        .then(data => {
            if (data.status !== 'success') {
                console.error('Failed to log question');
            }
            return data;
        })
        .catch(error => {
            console.error('Error logging question:', error);
            throw error;
        });
}

// Function to sync preferred links with backend
function syncPreferredLinks() {
    try {
        const preferredLinks = JSON.parse(localStorage.getItem('preferredLinks') || '[]');
        if (preferredLinks.length > 0) {
            return fetch('http://127.0.0.1:8000/api/sync_preferred_urls/', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ urls: preferredLinks })
            })
            .then(response => response.json())
            .catch(error => {
                console.error('Error syncing preferred links:', error);
            });
        }
    } catch (e) {
        console.error('Error reading preferred links for sync:', e);
    }
    return Promise.resolve();
}

export {
    postWebTextToServer,
    getChatResponse,
    clearMessages,
    getSourceUrls,
    logQuestion,
    setSessionId,
    syncPreferredLinks
};