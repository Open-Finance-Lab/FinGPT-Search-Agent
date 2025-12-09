// markdownRenderer.js
// Clean markdown + math rendering using markdown-it with texmath plugin

import markdownIt from 'markdown-it';
import texmath from 'markdown-it-texmath';

// Normalize math strings so KaTeX does not choke on uncommon unicode spacing/hyphen characters
function normalizeMathInput(mathText) {
  if (!mathText) {
    return mathText;
  }
  return mathText
    .replace(/\u202f/g, ' ') // narrow no-break space → regular space
    .replace(/\u2011/g, '-'); // non-breaking hyphen → regular hyphen
}

// KaTeX render options for the final math rendering
const KATEX_RENDER_OPTIONS = {
  delimiters: [
    { left: '$$', right: '$$', display: true },
    { left: '$', right: '$', display: false },
    { left: '\\[', right: '\\]', display: true },
    { left: '\\(', right: '\\)', display: false },
  ],
  throwOnError: false,
  errorColor: '#cc0000',
  strict: false,
  trust: true,
  macros: {
    '\\Δ': '\\Delta',
    '\\σ': '\\sigma',
    '\\ν': '\\nu',
    '\\ρ': '\\rho',
    '\\Γ': '\\Gamma',
    '\\Θ': '\\theta',
  },
  preProcess: normalizeMathInput,
};

// Create and configure the markdown-it instance
function createMarkdownRenderer() {
  const md = markdownIt({
    html: true,        // Enable HTML tags in source
    linkify: true,     // Autoconvert URL-like text to links
    typographer: false, // Disable typographic replacements to avoid conflicts
    breaks: false,     // Don't convert single '\n' to <br> (use double \n for paragraphs)
  });

  // Add the texmath plugin - this handles math at tokenization level
  // BEFORE any emphasis parsing, solving our asterisk problem
  md.use(texmath, {
    engine: {
      // We don't render here - just preserve the math for KaTeX
      renderToString: (tex, options) => {
        // Return the raw TeX wrapped in a span for KaTeX to find
        if (options.displayMode) {
          return `$$${tex}$$`;
        }
        return `$${tex}$`;
      },
    },
    delimiters: 'dollars', // Handles $...$ and $$...$$
  });

  return md;
}

// Singleton instance
let markdownRenderer = null;

function getMarkdownRenderer() {
  if (!markdownRenderer) {
    markdownRenderer = createMarkdownRenderer();
  }
  return markdownRenderer;
}

// Sanitize HTML to prevent XSS
function sanitizeHtml(html) {
  const template = document.createElement('template');
  template.innerHTML = html;

  // Remove dangerous elements
  const forbiddenSelectors = 'script,style,iframe,object,embed,link,meta';
  template.content.querySelectorAll(forbiddenSelectors).forEach((node) => node.remove());

  // Remove event handlers
  const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_ELEMENT, null, false);
  while (walker.nextNode()) {
    const element = walker.currentNode;
    Array.from(element.attributes).forEach((attr) => {
      if (attr.name.startsWith('on')) {
        element.removeAttribute(attr.name);
      }
    });
  }

  // Remove HTML comments
  const commentWalker = document.createTreeWalker(template.content, NodeFilter.SHOW_COMMENT, null, false);
  const comments = [];
  while (commentWalker.nextNode()) {
    comments.push(commentWalker.currentNode);
  }
  comments.forEach((node) => node.remove());

  return template.innerHTML;
}

// Apply target="_blank" to links for security
function applyLinkAttributes(element) {
  const links = element.querySelectorAll('a');
  links.forEach((link) => {
    link.setAttribute('target', '_blank');
    link.setAttribute('rel', 'noopener noreferrer');
  });
}

// Use KaTeX auto-render for final math rendering
function renderMath(element) {
  if (typeof globalThis.renderMathInElement !== 'function') {
    console.warn('KaTeX auto-render is not available.');
    return;
  }

  globalThis.renderMathInElement(element, KATEX_RENDER_OPTIONS);
}

// Apply optional prefix label
function applyPrefix(html, prefixLabel) {
  if (!prefixLabel) {
    return html;
  }
  return `<strong>${prefixLabel}:</strong> ${html}`;
}

// Core render function - MUCH simpler now!
function render(markdown, options = {}) {
  const { stabilizeStreaming = false } = options;

  // For streaming, append closing delimiters if needed
  let processedMarkdown = markdown || '';

  if (stabilizeStreaming) {
    // Simple checks for unclosed delimiters
    // markdown-it handles most cases well, but we help with streaming
    const dollarCount = (processedMarkdown.match(/\$/g) || []).length;
    if (dollarCount % 2 !== 0) {
      processedMarkdown += '$';
    }

    const fenceCount = (processedMarkdown.match(/```/g) || []).length;
    if (fenceCount % 2 !== 0) {
      processedMarkdown += '\n```';
    }
  }

  // Let markdown-it with texmath do ALL the work
  const md = getMarkdownRenderer();
  const html = md.render(processedMarkdown);

  return sanitizeHtml(html);
}

// Main export - renders final markdown content
export function renderMarkdownContent(targetElement, rawText, options = {}) {
  if (!targetElement) {
    return;
  }

  const { prefixLabel = 'FinGPT', wrapMath = true } = options;

  try {
    const html = render(rawText);
    targetElement.innerHTML = applyPrefix(html, prefixLabel);
    targetElement.dataset.renderState = 'final';

    applyLinkAttributes(targetElement);
    renderMath(targetElement);
  } catch (error) {
    console.error('Error rendering markdown:', error);
    // Fallback to plain text
    targetElement.textContent = `${prefixLabel ? `${prefixLabel}: ` : ''}${rawText || ''}`;
  }
}

// Export for streaming preview - uses same renderer with stabilization
export function renderStreamingPreview(targetElement, rawText, options = {}) {
  if (!targetElement) {
    return;
  }

  const { prefixLabel = 'FinGPT', wrapMath = true } = options;

  try {
    const html = render(rawText, { stabilizeStreaming: true });
    targetElement.innerHTML = applyPrefix(html, prefixLabel);
    targetElement.dataset.renderState = 'streaming';

    applyLinkAttributes(targetElement);
    renderMath(targetElement);
  } catch (error) {
    console.error('Error rendering streaming markdown:', error);
    // Fallback to plain text
    targetElement.textContent = `${prefixLabel ? `${prefixLabel}: ` : ''}${rawText || ''}`;
  }
}
