// api.js

// Function to POST JSON to the server endpoint
function postWebTextToServer(textContent, currentUrl) {
    return fetch("http://127.0.0.1:8000/input_webtext/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            textContent: textContent,
            currentUrl: currentUrl
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

// Function to get chat response from server
function getChatResponse(question, selectedModel, isAdvanced, useRAG) {
    const encodedQuestion = encodeURIComponent(question);
    const endpoint = isAdvanced ? 'get_adv_response' : 'get_chat_response';

    return fetch(
        `http://127.0.0.1:8000/${endpoint}/?question=${encodedQuestion}&models=${selectedModel}&is_advanced=${isAdvanced}&use_rag=${useRAG}`,
        { method: 'GET' }
    )
        .then(response => response.json())
        .catch(error => {
            console.error('There was a problem with your fetch operation:', error);
            throw error;
        });
}

// Function to clear messages
function clearMessages() {
    return fetch(`http://127.0.0.1:8000/clear_messages/`, { method: "POST" })
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
    return fetch(`http://127.0.0.1:8000/get_source_urls/?query=${String(searchQuery)}`, { method: "GET" })
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
        { method: "GET" }
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

// Function to add preferred URL
function addPreferredUrl(url) {
    return fetch('http://127.0.0.1:8000/api/add_preferred_url/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `url=${encodeURIComponent(url)}`
    })
        .then(response => response.json())
        .catch(error => {
            console.error('Error adding preferred link:', error);
            throw error;
        });
}

// Function to get preferred URLs
function getPreferredUrls() {
    return fetch('http://127.0.0.1:8000/api/get_preferred_urls/')
        .then(response => response.json())
        .catch(error => {
            console.error('Error loading preferred links:', error);
            throw error;
        });
}

export { 
    postWebTextToServer, 
    getChatResponse, 
    clearMessages, 
    getSourceUrls, 
    logQuestion,
    addPreferredUrl,
    getPreferredUrls
};