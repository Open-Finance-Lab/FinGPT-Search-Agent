// chat.js
import { submit_question, clear, get_sources } from '../helpers.js';

function createChatInterface(searchQuery) {
    const inputContainer = document.createElement('div');
    inputContainer.id = "inputContainer";

    // State for current mode
    let currentMode = 'Normal';  // Default to Normal mode

    const textbox = document.createElement("input");
    textbox.type = "text";
    textbox.id = "textbox";
    textbox.placeholder = "Type your question here...";
    textbox.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            submit_question(currentMode);
        }
    });
    inputContainer.appendChild(textbox);

    const buttonContainer = document.createElement('div');
    buttonContainer.id = "buttonContainer";

    // Create mode selector dropdown
    const modeSelector = document.createElement('div');
    modeSelector.id = 'modeSelector';
    modeSelector.className = 'mode-selector';

    // Main button that shows current mode
    const modeSelectorButton = document.createElement('button');
    modeSelectorButton.id = 'modeSelectorButton';
    modeSelectorButton.className = 'mode-selector-button mode-normal';

    const modeText = document.createElement('span');
    modeText.className = 'mode-text';
    modeText.innerText = currentMode;

    const modeArrow = document.createElement('span');
    modeArrow.className = 'mode-arrow';
    modeArrow.innerHTML = '▲';

    modeSelectorButton.appendChild(modeText);
    modeSelectorButton.appendChild(modeArrow);

    // Dropdown menu
    const modeDropdown = document.createElement('div');
    modeDropdown.id = 'modeDropdown';
    modeDropdown.className = 'mode-dropdown';
    modeDropdown.style.display = 'none';

    // Normal mode option
    const normalOption = document.createElement('div');
    normalOption.className = 'mode-option mode-option-selected';
    normalOption.dataset.mode = 'Normal';

    const normalCheckmark = document.createElement('span');
    normalCheckmark.className = 'mode-checkmark';
    normalCheckmark.innerHTML = '✓';

    const normalText = document.createElement('span');
    normalText.className = 'mode-option-text';
    normalText.innerText = 'Normal';

    normalOption.appendChild(normalText);
    normalOption.appendChild(normalCheckmark);

    // Extensive mode option
    const extensiveOption = document.createElement('div');
    extensiveOption.className = 'mode-option';
    extensiveOption.dataset.mode = 'Extensive';

    const extensiveCheckmark = document.createElement('span');
    extensiveCheckmark.className = 'mode-checkmark';
    extensiveCheckmark.innerHTML = '✓';
    extensiveCheckmark.style.visibility = 'hidden';

    const extensiveText = document.createElement('span');
    extensiveText.className = 'mode-option-text';
    extensiveText.innerText = 'Extensive';

    extensiveOption.appendChild(extensiveText);
    extensiveOption.appendChild(extensiveCheckmark);

    modeDropdown.appendChild(normalOption);
    modeDropdown.appendChild(extensiveOption);

    modeSelector.appendChild(modeSelectorButton);
    modeSelector.appendChild(modeDropdown);

    // Toggle dropdown on button click
    modeSelectorButton.onclick = function(e) {
        e.stopPropagation();
        const isOpen = modeDropdown.style.display !== 'none';
        if (isOpen) {
            modeDropdown.style.display = 'none';
            modeArrow.innerHTML = '▲';
        } else {
            modeDropdown.style.display = 'block';
            modeArrow.innerHTML = '▼';
        }
    };

    // Handle mode selection
    [normalOption, extensiveOption].forEach(option => {
        option.onclick = function(e) {
            e.stopPropagation();
            const selectedMode = this.dataset.mode;

            // Update current mode
            currentMode = selectedMode;
            modeText.innerText = currentMode;

            // Update button styling
            if (currentMode === 'Normal') {
                modeSelectorButton.className = 'mode-selector-button mode-normal';
            } else {
                modeSelectorButton.className = 'mode-selector-button mode-extensive';
            }

            // Update checkmarks
            if (currentMode === 'Normal') {
                normalOption.classList.add('mode-option-selected');
                extensiveOption.classList.remove('mode-option-selected');
                normalCheckmark.style.visibility = 'visible';
                extensiveCheckmark.style.visibility = 'hidden';
            } else {
                normalOption.classList.remove('mode-option-selected');
                extensiveOption.classList.add('mode-option-selected');
                normalCheckmark.style.visibility = 'hidden';
                extensiveCheckmark.style.visibility = 'visible';
            }

            // Close dropdown
            modeDropdown.style.display = 'none';
            modeArrow.innerHTML = '▲';
        };
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!modeSelector.contains(e.target)) {
            modeDropdown.style.display = 'none';
            modeArrow.innerHTML = '▲';
        }
    });

    // Create mode label
    const modeLabel = document.createElement('span');
    modeLabel.className = 'mode-label';
    modeLabel.innerText = 'Mode:';

    buttonContainer.appendChild(modeLabel);
    buttonContainer.appendChild(modeSelector);

    const buttonRow = document.createElement('div');
    buttonRow.className = "button-row";

    const clearButton = document.createElement('button');
    clearButton.innerText = "Clear";
    clearButton.className = "clear-button";
    clearButton.onclick = clear;

    const sourcesButton = document.createElement('button');
    sourcesButton.innerText = "Sources";
    sourcesButton.className = "sources-button";
    sourcesButton.onclick = function () { get_sources(searchQuery); };

    buttonRow.appendChild(sourcesButton);
    buttonRow.appendChild(clearButton);

    return { inputContainer, buttonContainer, buttonRow };
}

export { createChatInterface };
