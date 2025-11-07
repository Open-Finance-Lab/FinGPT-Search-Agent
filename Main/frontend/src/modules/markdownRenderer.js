// markdownRenderer.js
// Centralized Markdown + math rendering that relies on self-hosted UMD builds.

const MARKDOWN_OPTIONS = {
  gfm: true,
  breaks: true,
  mangle: false,
  headerIds: false,
};

const MATH_PLACEHOLDER_PREFIX = '__MATH_BLOCK_';

const DEFAULT_MATH_RENDER_OPTIONS = {
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
};

function countOccurrences(haystack, needle) {
  if (!haystack || !needle) {
    return 0;
  }
  return haystack.split(needle).length - 1;
}

function stripAllOccurrences(text, token) {
  if (!text || !token) {
    return text;
  }
  return text.split(token).join('');
}

function stabilizeStreamingDelimiters(text) {
  if (!text) {
    return text;
  }

  const suffixes = [];
  const append = (token) => {
    if (token) {
      suffixes.push(token);
    }
  };

  const codeFenceCount = countOccurrences(text, '```');
  if (codeFenceCount % 2 !== 0) {
    append('\n```');
  }

  const tildeFenceCount = countOccurrences(text, '~~~');
  if (tildeFenceCount % 2 !== 0) {
    append('\n~~~');
  }

  const mathFenceCount = countOccurrences(text, '$$');
  if (mathFenceCount % 2 !== 0) {
    append('\n$$');
  }

  let inlineScan = stripAllOccurrences(text, '```');
  inlineScan = stripAllOccurrences(inlineScan, '~~~');

  const inlineCodeCount = countOccurrences(inlineScan, '`');
  if (inlineCodeCount % 2 !== 0) {
    append('`');
  }
  inlineScan = stripAllOccurrences(inlineScan, '`');

  let emphasisScan = inlineScan;

  const doubleAsteriskCount = countOccurrences(emphasisScan, '**');
  if (doubleAsteriskCount % 2 !== 0) {
    append('**');
  }
  emphasisScan = stripAllOccurrences(emphasisScan, '**');

  const doubleUnderscoreCount = countOccurrences(emphasisScan, '__');
  if (doubleUnderscoreCount % 2 !== 0) {
    append('__');
  }
  emphasisScan = stripAllOccurrences(emphasisScan, '__');

  const strikeCount = countOccurrences(emphasisScan, '~~');
  if (strikeCount % 2 !== 0) {
    append('~~');
  }
  emphasisScan = stripAllOccurrences(emphasisScan, '~~');

  const singleAsteriskCount = countOccurrences(emphasisScan, '*');
  if (singleAsteriskCount % 2 !== 0) {
    append('*');
  }
  emphasisScan = stripAllOccurrences(emphasisScan, '*');

  const singleUnderscoreCount = countOccurrences(emphasisScan, '_');
  if (singleUnderscoreCount % 2 !== 0) {
    append('_');
  }

  if (suffixes.length === 0) {
    return text;
  }

  return `${text}${suffixes.join('')}`;
}

function getMarked() {
  const globalMarked = globalThis.marked?.marked || globalThis.marked;
  if (!globalMarked || typeof globalMarked.parse !== 'function') {
    console.warn('Marked UMD bundle is not available in the current context.');
    return null;
  }
  return globalMarked;
}

function normalizeEmphasisDelimiters(text) {
  if (!text) {
    return text;
  }

  let normalized = text.replace(/\*(?:\s*\*)+/g, (match) => match.replace(/\s+/g, ''));

  normalized = normalized.replace(/(\*{2,})([ \t]+)(?=\S)/g, '$1');
  normalized = normalized.replace(/(?<=\S)([ \t]+)(\*{2,})/g, (_match, _spaces, stars) => stars);

  return normalized;
}

function autoWrapMathExpressions(text) {
  if (!text) {
    return text;
  }

  let processed = text.replace(
    /(?<!\$)([^\s$])([^$\n]+?)(?<!\$)([^\s$])/g,
    (match, p1, p2, p3) => {
      if (/[∂σ²∆ΓΘνρ√]|\b[dN]_[12]\b|\bln\b|\be\^/.test(match)) {
        return `${p1}$${p2}${p3}$`;
      }
      return match;
    }
  );

  processed = processed.replace(/^\s*([^$\n]+?)\s*$/gm, (match) => {
    if (/[∂σ²∆ΓΘνρ√=−].*[∂σ²∆ΓΘνρ√=−]/.test(match) && !/\$\$.*\$\$/.test(match)) {
      return `$$${match}$$`;
    }
    return match;
  });

  return processed;
}

function extractMathBlocks(text) {
  const blocks = [];
  const patterns = [
    /\\\[([\s\S]+?)\\\]/g, // \[...\]
    /\$\$([\s\S]+?)\$\$/g, // $$...$$
    /\\\(([\s\S]+?)\\\)/g, // \(...\)
    /\$([^\$\n]+?)\$/g, // $...$
  ];

  let processedText = text;
  const toPlaceholder = (match) => {
    const token = `${MATH_PLACEHOLDER_PREFIX}${blocks.length}__`;
    blocks.push(match);
    return token;
  };

  patterns.forEach((regex) => {
    processedText = processedText.replace(regex, (match) => toPlaceholder(match));
  });

  return { processedText, blocks };
}

function restoreMathBlocks(html, blocks) {
  return blocks.reduce((acc, block, index) => {
    const token = `${MATH_PLACEHOLDER_PREFIX}${index}__`;
    return acc.split(token).join(block);
  }, html);
}

function sanitizeHtml(html) {
  const template = document.createElement('template');
  template.innerHTML = html;

  const forbiddenSelectors = 'script,style,iframe,object,embed,link,meta';
  template.content.querySelectorAll(forbiddenSelectors).forEach((node) => node.remove());

  const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_ELEMENT, null, false);
  while (walker.nextNode()) {
    const element = walker.currentNode;
    Array.from(element.attributes).forEach((attr) => {
      if (attr.name.startsWith('on')) {
        element.removeAttribute(attr.name);
      }
    });
  }

  const commentWalker = document.createTreeWalker(template.content, NodeFilter.SHOW_COMMENT, null, false);
  const comments = [];
  while (commentWalker.nextNode()) {
    comments.push(commentWalker.currentNode);
  }
  comments.forEach((node) => node.remove());

  return template.innerHTML;
}

function applyLinkAttributes(element) {
  const links = element.querySelectorAll('a');
  links.forEach((link) => {
    link.setAttribute('target', '_blank');
    link.setAttribute('rel', 'noopener noreferrer');
  });
}

function renderMath(element) {
  if (typeof globalThis.renderMathInElement !== 'function') {
    console.warn('KaTeX auto-render is not available.');
    return;
  }

  globalThis.renderMathInElement(element, DEFAULT_MATH_RENDER_OPTIONS);
}

function buildContentHtml(markedInstance, source, { wrapMath, stabilizeStreaming = false }) {
  const normalized = normalizeEmphasisDelimiters(source || '');
  const mathWrapped = wrapMath ? autoWrapMathExpressions(normalized) : normalized;
  const { processedText, blocks } = extractMathBlocks(mathWrapped);

  const textForMarked = stabilizeStreaming
    ? stabilizeStreamingDelimiters(processedText)
    : processedText;

  let html = markedInstance.parse(textForMarked, MARKDOWN_OPTIONS);
  html = restoreMathBlocks(html, blocks);
  return sanitizeHtml(html);
}

function applyPrefix(html, prefixLabel) {
  if (!prefixLabel) {
    return html;
  }
  return `<strong>${prefixLabel}:</strong> ${html}`;
}

export function renderMarkdownContent(targetElement, rawText, options = {}) {
  if (!targetElement) {
    return;
  }

  const { prefixLabel = 'FinGPT', wrapMath = true } = options;
  const markedInstance = getMarked();
  if (!markedInstance) {
    targetElement.textContent = `${prefixLabel ? `${prefixLabel}: ` : ''}${rawText || ''}`;
    return;
  }

  const html = buildContentHtml(markedInstance, rawText, { wrapMath });
  targetElement.innerHTML = applyPrefix(html, prefixLabel);
  targetElement.dataset.renderState = 'final';

  applyLinkAttributes(targetElement);
  renderMath(targetElement);
}

export function renderStreamingPreview(targetElement, rawText, options = {}) {
  if (!targetElement) {
    return;
  }

  const { prefixLabel = 'FinGPT', wrapMath = true } = options;
  const prefix = prefixLabel ? `${prefixLabel}: ` : '';
  const markedInstance = getMarked();

  if (!markedInstance) {
    targetElement.textContent = `${prefix}${rawText || ''}`;
    targetElement.dataset.renderState = 'streaming';
    return;
  }

  const html = buildContentHtml(markedInstance, rawText, {
    wrapMath,
    stabilizeStreaming: true,
  });
  targetElement.innerHTML = applyPrefix(html, prefixLabel);
  targetElement.dataset.renderState = 'streaming';

  applyLinkAttributes(targetElement);
  renderMath(targetElement);
}
