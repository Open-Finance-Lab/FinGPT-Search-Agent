# Switching The Browser Extension Between Cloud And Local Backends

The Agentic FinSearch browser extension now defaults to the hosted production backend at `https://agenticfinsearch.org`. Developers can override that target at runtime without rebuilding the bundle.

## Quick Reference

- **Production (default)** – no action required; the extension calls `https://agenticfinsearch.org`.
- **Local development** – point the extension back to your machine:  
  ```js
  // Run in the browser console on any page where the content script loads
  localStorage.setItem('agenticBackendUrl', 'http://127.0.0.1:8000');
  location.reload();
  ```
- **Custom staging URL** – replace the value above with your target, for example:  
  ```js
  localStorage.setItem('agenticBackendUrl', 'https://staging.agenticfinsearch.org');
  location.reload();
  ```
- **Revert to default** – remove the override and reload:  
  ```js
  localStorage.removeItem('agenticBackendUrl');
  location.reload();
  ```

## How It Works

1. The content script resolves the backend base URL in this order:
   - `window.AGENTIC_BACKEND_URL` (if set before the script runs – mainly useful for automated tests).
   - `localStorage.agenticBackendUrl`, if it contains a valid absolute URL.
   - The baked-in default (`https://agenticfinsearch.org`).
2. Every fetch/EventSource call is constructed from that resolved base URL, so the change applies everywhere with a reload.

## Tips

- Use `http://127.0.0.1:8000` instead of `http://localhost:8000` for local testing to avoid mixed hostnames with cookie scope; the extension’s manifest already permits both.
- When switching frequently, consider keeping a small helper snippet in your browser console history or DevTools snippets.
- After changing the override, reload the active tab (or disable/enable the extension) so the new base URL is applied to the running content script.
