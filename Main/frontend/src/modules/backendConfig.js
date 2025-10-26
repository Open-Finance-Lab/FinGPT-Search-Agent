// backendConfig.js
// Central place to resolve the backend base URL used by the extension.

const DEFAULT_BACKEND_BASE_URL = 'https://agenticfinsearch.org';
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
        const pathname = parsed.pathname === '/' ? '' : parsed.pathname.replace(/\/$/, '');
        return `${parsed.protocol}//${parsed.host}${pathname}`;
    } catch (error) {
        console.warn('Ignoring invalid backend URL override:', url, error);
        return null;
    }
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
        console.debug('Unable to read backend URL override from localStorage:', error);
    }

    return null;
}

function getBackendBaseUrl() {
    if (!cachedBaseUrl) {
        cachedBaseUrl = resolveOverride() ?? DEFAULT_BACKEND_BASE_URL;
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

export { getBackendBaseUrl, buildBackendUrl };
