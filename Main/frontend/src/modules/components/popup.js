// popup.js
import { renderMarkdownContent } from '../markdownRenderer.js';

function createPopup() {
    const popup = document.createElement('div');
    popup.id = "draggableElement";
    return popup;
}

export { createPopup };

export function initPopup() {
  console.log("Popup initialized");
}

// Example function that might display a message
// Assumes containerElement is the parent DOM element where messages are appended,
// messageText is the raw string for the message, and sender is e.g., 'user' or 'bot'.
export function displayChatMessage(containerElement, messageText, sender) {
  const messageElement = document.createElement('div');
  messageElement.classList.add('message', `message-${sender}`);

  renderMarkdownContent(messageElement, messageText, {
    prefixLabel: sender === 'bot' ? 'FinGPT' : null,
  });

  containerElement.appendChild(messageElement);
}
