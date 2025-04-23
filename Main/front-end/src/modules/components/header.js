// header.js
function createHeader(popup, settings_window, settingsIcon, positionModeIcon, isFixedModeRef) {
    const header = document.createElement('div');
    header.id = "header";
    header.className = "draggable";

    const title = document.createElement('span');
    title.innerText = "FinGPT";

    const iconContainer = document.createElement('div');
    iconContainer.id = "icon-container";

    const minimizeIcon = document.createElement('span');
    minimizeIcon.innerText = "➖";
    minimizeIcon.className = "icon";
    minimizeIcon.onclick = function () {
        if (popup.classList.contains('minimized')) {
            popup.classList.remove('minimized');
            popup.style.height = '600px';
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

    iconContainer.appendChild(settingsIcon);
    iconContainer.appendChild(positionModeIcon);
    iconContainer.appendChild(minimizeIcon);
    iconContainer.appendChild(closeIcon);

    header.appendChild(title);
    header.appendChild(iconContainer);

    return header;
}

export { createHeader };
