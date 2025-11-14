// backendConfig.js
// Central place to resolve the backend base URL used by the extension.

const DEFAULT_BACKEND_BASE_URL = 'https://agenticfinsearch.org';
const LOCAL_BACKEND_URL = 'http://localhost:8000';
let cachedBaseUrl = null;

function normalizeBaseUrl(url) {
  if (!url) {
    return null;
  }

  try {
    const trimmed = url.trim();
    if (!trimmed) {
      return null;
    }

    const parsed = new URL(trimmed);
    const pathname =
      parsed.pathname === '/' ? '' : parsed.pathname.replace(/\/$/, '');
    return `${parsed.protocol}//${parsed.host}${pathname}`;
  } catch (error) {
    console.warn('Ignoring invalid backend URL override:', url, error);
    return null;
  }
}

async function checkLocalBackend() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 800); // 800ms timeout

    const response = await fetch(`${LOCAL_BACKEND_URL}/health/`, {
      method: 'GET',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (response.ok) {
      console.log('✅ Local backend detected at localhost:8000');
      return true;
    }
  } catch (error) {
    // Local backend not available, that's fine
  }
  return false;
}

function resolveOverride() {
  if (typeof window === 'undefined') {
    return null;
  }

  if (window.AGENTIC_BACKEND_URL) {
    const override = normalizeBaseUrl(window.AGENTIC_BACKEND_URL);
    if (override) {
      return override;
    }
  }

  try {
    const stored = window.localStorage?.getItem('agenticBackendUrl');
    const override = normalizeBaseUrl(stored);
    if (override) {
      return override;
    }
  } catch (error) {
    console.debug(
      'Unable to read backend URL override from localStorage:',
      error
    );
  }

  return null;
}

function getBackendBaseUrl() {
  if (!cachedBaseUrl) {
    // Check for manual override first
    const override = resolveOverride();
    cachedBaseUrl = override || DEFAULT_BACKEND_BASE_URL;
  }
  return cachedBaseUrl;
}

function buildBackendUrl(path = '/') {
  const baseUrl = getBackendBaseUrl();
  if (!path) {
    return baseUrl;
  }
  const sanitizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${sanitizedPath}`;
}

// Auto-detect local backend on load
(async function initBackend() {
  // If there's a manual override, use it
  if (resolveOverride()) {
    return;
  }

  // Check if local backend is available
  const isLocalAvailable = await checkLocalBackend();
  if (isLocalAvailable) {
    cachedBaseUrl = LOCAL_BACKEND_URL;
    console.log('🚀 Using local backend:', LOCAL_BACKEND_URL);
  } else {
    cachedBaseUrl = DEFAULT_BACKEND_BASE_URL;
    console.log('🌐 Using production backend:', DEFAULT_BACKEND_BASE_URL);
  }
})();

export { getBackendBaseUrl, buildBackendUrl };
