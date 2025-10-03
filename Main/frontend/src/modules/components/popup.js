// popup.js
import { marked } from 'marked';
import renderMathInElement from 'katex/dist/contrib/auto-render';
import 'katex/dist/katex.min.css';

function createPopup() {
    const popup = document.createElement('div');
    popup.id = "draggableElement";
    return popup;
}

export { createPopup };

export function initPopup() {
  console.log("Popup initialized");
}

// Helper function to wrap math expressions in proper LaTeX delimiters
function formatMathExpressions(text) {
  // Replace inline math expressions that aren't already wrapped
  text = text.replace(/(?<!\$)([^\s$])([^$\n]+?)(?<!\$)([^\s$])/g, (match, p1, p2, p3) => {
    // Check if this contains math symbols
    if (/[∂σ²∆ΓΘνρ√]|\b[dN]_[12]\b|\bln\b|\be\^/.test(match)) {
      return `${p1}$${p2}${p3}$`;
    }
    return match;
  });

  // Replace display math expressions (equations on their own line)
  text = text.replace(/^\s*([^$\n]+?)\s*$/gm, (match) => {
    if (/[∂σ²∆ΓΘνρ√=−].*[∂σ²∆ΓΘνρ√=−]/.test(match) && !/\$\$.*\$\$/.test(match)) {
      return `$$${match}$$`;
    }
    return match;
  });

  return text;
}

// Example function that might display a message
// Assumes containerElement is the parent DOM element where messages are appended,
// messageText is the raw string for the message, and sender is e.g., 'user' or 'bot'.
export function displayChatMessage(containerElement, messageText, sender) {
  const messageElement = document.createElement('div');
  messageElement.classList.add('message', `message-${sender}`);

  // 1. Format math expressions with proper LaTeX delimiters
  const formattedText = formatMathExpressions(messageText);

  // 2. Convert Markdown to HTML
  const markdownHtml = marked.parse(formattedText, { 
    gfm: true, 
    breaks: true,
    mangle: false,
    headerIds: false
  });
  messageElement.innerHTML = markdownHtml;

  containerElement.appendChild(messageElement);

  // 3. Render LaTeX within the newly added message element
  renderMathInElement(messageElement, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "$", right: "$", display: false },
      { left: "\\(", right: "\\)", display: false },
      { left: "\\[", right: "\\]", display: true }
    ],
    output: 'html',
    throwOnError: false,
    errorColor: '#cc0000',
    macros: {
      '\\Δ': '\\Delta',
      '\\σ': '\\sigma',
      '\\ν': '\\nu',
      '\\ρ': '\\rho',
      '\\Γ': '\\Gamma',
      '\\Θ': '\\theta'
    },
    trust: true,
    strict: false
  });
}
