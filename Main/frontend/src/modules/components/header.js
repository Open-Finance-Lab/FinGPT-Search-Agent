// header.js
function createHeader(popup, settings_window, settingsButton, positionModeButton, isFixedModeRef, defaultHeight) {
    const expandedHeight = defaultHeight ?? '520px';
    const header = document.createElement('div');
    header.id = "header";
    header.className = "draggable";

    const title = document.createElement('span');
    title.innerText = "Agentic FinSearch";

    const iconContainer = document.createElement('div');
    iconContainer.id = "icon-container";

    const minimizeIcon = document.createElement('span');
    minimizeIcon.innerText = "➖";
    minimizeIcon.className = "icon";
    minimizeIcon.onclick = function () {
        if (popup.classList.contains('minimized')) {
            popup.classList.remove('minimized');
            popup.style.height = expandedHeight;
        } else {
            popup.classList.add('minimized');
            popup.style.height = '60px';
        }
    };

    const closeIcon = document.createElement('span');
    closeIcon.innerText = "❌";
    closeIcon.className = "icon";
    closeIcon.onclick = function () {
        popup.style.display = 'none';
    };

    const loadingContainer = document.createElement('div');
    loadingContainer.id = "auto-scrape-loading";
    loadingContainer.style.display = "none"; // Hidden by default
    loadingContainer.className = "loading-container";

    const loadingText = document.createElement('span');
    loadingText.innerText = "Scraping current page...";
    loadingText.className = "loading-text";

    const spinner = document.createElement('div');
    spinner.className = "spinner-small";

    loadingContainer.appendChild(loadingText);
    loadingContainer.appendChild(spinner);

    iconContainer.appendChild(loadingContainer);
    iconContainer.appendChild(settingsButton);
    iconContainer.appendChild(positionModeButton);
    iconContainer.appendChild(minimizeIcon);
    iconContainer.appendChild(closeIcon);

    header.appendChild(title);
    header.appendChild(iconContainer);

    return header;
}

export { createHeader };
