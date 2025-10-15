// chat.js
import { submit_question, clear, get_sources } from '../helpers.js';

function createChatInterface(searchQuery) {
    const inputContainer = document.createElement('div');
    inputContainer.id = "inputContainer";

    // State for current mode
    let currentMode = 'Thinking';  // Default to Thinking mode

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
    modeSelectorButton.className = 'mode-selector-button mode-thinking';

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

    // Thinking mode option
    const thinkingOption = document.createElement('div');
    thinkingOption.className = 'mode-option mode-option-selected';
    thinkingOption.dataset.mode = 'Thinking';

    const thinkingCheckmark = document.createElement('span');
    thinkingCheckmark.className = 'mode-checkmark';
    thinkingCheckmark.innerHTML = '✓';

    const thinkingText = document.createElement('span');
    thinkingText.className = 'mode-option-text';
    thinkingText.innerText = 'Thinking';

    thinkingOption.appendChild(thinkingText);
    thinkingOption.appendChild(thinkingCheckmark);

    // Research mode option
    const researchOption = document.createElement('div');
    researchOption.className = 'mode-option';
    researchOption.dataset.mode = 'Research';

    const researchCheckmark = document.createElement('span');
    researchCheckmark.className = 'mode-checkmark';
    researchCheckmark.innerHTML = '✓';
    researchCheckmark.style.visibility = 'hidden';

    const researchText = document.createElement('span');
    researchText.className = 'mode-option-text';
    researchText.innerText = 'Research';

    researchOption.appendChild(researchText);
    researchOption.appendChild(researchCheckmark);

    modeDropdown.appendChild(thinkingOption);
    modeDropdown.appendChild(researchOption);

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
    [thinkingOption, researchOption].forEach(option => {
        option.onclick = function(e) {
            e.stopPropagation();
            const selectedMode = this.dataset.mode;

            // Update current mode
            currentMode = selectedMode;
            modeText.innerText = currentMode;

            // Update button styling
            if (currentMode === 'Thinking') {
                modeSelectorButton.className = 'mode-selector-button mode-thinking';
            } else {
                modeSelectorButton.className = 'mode-selector-button mode-research';
            }

            // Update checkmarks
            if (currentMode === 'Thinking') {
                thinkingOption.classList.add('mode-option-selected');
                researchOption.classList.remove('mode-option-selected');
                thinkingCheckmark.style.visibility = 'visible';
                researchCheckmark.style.visibility = 'hidden';
            } else {
                thinkingOption.classList.remove('mode-option-selected');
                researchOption.classList.add('mode-option-selected');
                thinkingCheckmark.style.visibility = 'hidden';
                researchCheckmark.style.visibility = 'visible';
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
