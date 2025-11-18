// layoutState.js
// Persists popup layout per page using the built-in extension storage (no extra backend).

const STORAGE_NAMESPACE = 'fingpt_layout_v1';

function getLayoutKeyForUrl(url = window.location.href) {
    try {
        const { origin, pathname } = new URL(url);
        return `${origin}${pathname}`;
    } catch (error) {
        console.warn('Failed to normalize URL for layout key:', error);
        return url || 'unknown';
    }
}

function getStorageArea() {
    if (typeof chrome !== 'undefined' && chrome?.storage?.local) {
        return chrome.storage.local;
    }
    return null;
}

function buildStorageKey(url = window.location.href) {
    const pageKey = getLayoutKeyForUrl(url);
    return `${STORAGE_NAMESPACE}:${pageKey}`;
}

async function loadLayoutState(url = window.location.href) {
    const storageKey = buildStorageKey(url);
    const storage = getStorageArea();

    if (storage) {
        return new Promise((resolve) => {
            storage.get([storageKey], (result) => {
                resolve(result?.[storageKey] || null);
            });
        });
    }

    try {
        const raw = window.localStorage?.getItem(storageKey);
        return raw ? JSON.parse(raw) : null;
    } catch (error) {
        console.warn('Failed to load layout state from localStorage:', error);
        return null;
    }
}

async function saveLayoutState(state, url = window.location.href) {
    if (!state) {
        return;
    }

    const storageKey = buildStorageKey(url);
    const storage = getStorageArea();

    if (storage) {
        return new Promise((resolve) => {
            storage.set({ [storageKey]: state }, () => resolve());
        });
    }

    try {
        window.localStorage?.setItem(storageKey, JSON.stringify(state));
    } catch (error) {
        console.warn('Failed to persist layout state to localStorage:', error);
    }
}

export { getLayoutKeyForUrl, loadLayoutState, saveLayoutState };
