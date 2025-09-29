// settings_window.js
import { availableModels, selectedModel, setSelectedModel, fetchAvailableModels, getAvailableModels, getModelDetails } from '../config.js';
//import { loadPreferredLinks, createAddLinkButton } from '../helpers.js';
import { createLinkManager } from './link_manager.js';

// Extract text from pdf and docx
// import * as pdfjsLib from "https://cdn.jsdelivr.net/npm/pdfjs-dist@2.11.338/es5/build/pdf.js";
// import { mammoth } from 'https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.4.2/mammoth.browser.min.js';

function createSettingsWindow(isFixedModeRef, settingsIcon, positionModeIcon) {
    const settings_window = document.createElement('div');
    settings_window.style.display = "none";
    settings_window.id = "settings_window";

    const label = document.createElement('label');
    label.className = 'settings-checkbox-label';
    label.innerText = "Light Mode";
    const lightSwitch = document.createElement('input');
    lightSwitch.type = "checkbox";
    lightSwitch.onchange = () => document.body.classList.toggle('light-mode');
    label.appendChild(lightSwitch);
    settings_window.appendChild(label);

    const modelContainer = document.createElement('div');
    modelContainer.id = "model_selection_container";

    const modelHeader = document.createElement('div');
    modelHeader.id = "model_selection_header";
    modelHeader.innerText = `Model: ${selectedModel}`;

    const modelToggleIcon = document.createElement('span');
    modelToggleIcon.innerText = "⯆";

    modelHeader.appendChild(modelToggleIcon);
    modelContainer.appendChild(modelHeader);

    const modelContent = document.createElement('div');
    modelContent.id = "model_selection_content";
    modelContent.style.display = "none";

    function handleModelSelection(modelItem, modelName) {
        document.querySelectorAll('.model-selection-item').forEach(item => item.classList.remove('selected-model'));
        setSelectedModel(modelName);
        modelItem.classList.add('selected-model');
        modelHeader.innerText = `Model: ${modelName}`;
        modelHeader.appendChild(modelToggleIcon);
    }

    // Function to populate model list
    async function populateModelList() {
        // Clear existing items
        modelContent.innerHTML = '';
        
        try {
            // Fetch models from backend
            await fetchAvailableModels();
            const models = getAvailableModels();
            
            const modelDetails = getModelDetails();
            
            models.forEach(model => {
                const item = document.createElement('div');
                item.className = 'model-selection-item';
                
                // Use description if available, otherwise just the model ID
                const details = modelDetails[model];
                if (details && details.description) {
                    item.innerHTML = `<strong>${model}</strong><br><small style="color: #888;">${details.description}</small>`;
                } else {
                    item.innerText = model;
                }
                
                if (model === selectedModel) item.classList.add('selected-model');
                item.onclick = () => handleModelSelection(item, model);
                modelContent.appendChild(item);
            });
        } catch (error) {
            console.error("Failed to populate model list:", error);
            modelContent.innerHTML = '<div style="color: red; padding: 10px;">Error: Unable to fetch models from backend</div>';
        }
    }

    // Populate model list when settings window is created
    populateModelList();

    modelContainer.appendChild(modelContent);
    settings_window.appendChild(modelContainer);

    modelHeader.onclick = () => {
        modelContent.style.display = modelContent.style.display === "none" ? "block" : "none";
        modelToggleIcon.innerText = modelContent.style.display === "none" ? "⯆" : "⯅";
    };

    const preferredLinksContainer = document.createElement('div');
    preferredLinksContainer.id = "preferred_links_container";

    const preferredLinksHeader = document.createElement('div');
    preferredLinksHeader.id = "preferred_links_header";
    preferredLinksHeader.innerText = "Preferred Links";

    const toggleIcon = document.createElement('span');
    toggleIcon.innerText = "⯆";
    preferredLinksHeader.appendChild(toggleIcon);
    preferredLinksContainer.appendChild(preferredLinksHeader);

    //const preferredLinksContent = document.createElement('div');
    //preferredLinksContent.id = "preferred_links_content";

    const linkManager = createLinkManager();
    linkManager.id = "preferred_links_content";
    linkManager.style.display = "none";
    preferredLinksContainer.appendChild(linkManager);
    settings_window.appendChild(preferredLinksContainer);

    preferredLinksHeader.onclick = function () {
        const isHidden = linkManager.style.display === "none";
        linkManager.style.display = isHidden ? "block" : "none";
        toggleIcon.innerText = isHidden ? "⯅" : "⯆";
    };

    // Set workerSrc to load PDF.js worker from CDN
    // pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.11.338/pdf.worker.min.js';
    async function extractTextFromPDF(file) {
        
        // Access global libraries from window
        // Check if libraries are available
        // In newer versions of PDF.js, the library might be accessible as window.pdfjsLib or just pdf
        const pdfjsLib = window.pdfjsLib || window.pdf || window.pdfjsNamespace;

        console.log("PDF.js loaded:", typeof pdfjsLib !== 'undefined');
        console.log("Mammoth loaded:", typeof window.mammoth !== 'undefined');

        
        // Set worker path - this is crucial for PDF.js to work
        if (pdfjsLib) {
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        }

        const arrayBuffer = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        let text = '';

        for (let i = 0; i < pdf.numPages; i++) {
            const page = await pdf.getPage(i + 1);
            const content = await page.getTextContent();
            const pageText = content.items.map(item => item.str).join(' ');
            text += pageText + '\n';
        }
        return text;
    }

    async function extractTextFromDocx(file) {
    const arrayBuffer = await file.arrayBuffer();
    const result = await mammoth.extractRawText({ arrayBuffer });
    return result.value;
    }



    // —– MCP Mode Toggle —–
    const mcpLabel = document.createElement('label');
    mcpLabel.className = 'settings-checkbox-label';
    mcpLabel.innerText = "MCP Mode";
    const mcpSwitch = document.createElement('input');
    mcpSwitch.type = "checkbox";
    mcpSwitch.id = "mcpModeSwitch";
    mcpLabel.appendChild(mcpSwitch);



    // Local RAG Upload
    let RAGPath = '';

    const ragLabel = document.createElement('label');
    ragLabel.className = 'settings-checkbox-label';
    ragLabel.innerText = "Local RAG";
    ragLabel.setAttribute('for', 'ragSwitch');

    const ragSwitch = document.createElement('input');
    ragSwitch.type = "checkbox";
    ragSwitch.name = "ragSwitch";
    ragSwitch.id = "ragSwitch";
    ragSwitch.style.transform = 'translate(5px, 2px)';
    ragSwitch.disabled = true;
    ragSwitch.onchange = async function() {
        // Any immediate actions when the checkbox changes can be handled here
        console.log ("switch value:", ragSwitch.checked);

        
        if(ragSwitch.checked && RAGPath !== '') {
            console.log("BODY:", JSON.stringify({ 'filePaths': [RAGPath] }));
        
            // Retrieve all file contents
            const fileHandles = [];
            for await (const entry of RAGPath.values()) {
                if (entry.kind === 'file') {
                    fileHandles.push(entry);  // Store file handles
                }
            }
            const filesPromises = fileHandles.map(async (handle) => {
                const file = await handle.getFile();
                const ext = file.name.split('.').pop().toLowerCase();
                console.log(`[DEBUG] extension: ${ext}`)
                let text = "hello";
                if (ext === 'txt') {
                    text = await file.text();
                } else if (ext === 'pdf') {
                    text = await extractTextFromPDF(file);
                } else if (ext === 'docx') {
                    text = await extractTextFromDocx(file);
                } else {
                    console.warn(`Unsupported file type: ${file.name}`);
                }
                console.log(`[DEBUG] extension: ${text}`)
                return { name: file.name, content: text };
            });
            const filesData = await Promise.all(filesPromises);
            console.log("filesdata: ", filesData);
            
            // Create a FormData object
            const formData = new FormData();

            // Convert your data to a JSON string and add it as a file
            const jsonBlob = new Blob([JSON.stringify({ 'filePaths': filesData })], 
                            { type: 'application/json' });
            formData.append('json_data', jsonBlob, 'data.json');

            // Making the POST request to Flask
            fetch('http://127.0.0.1:8000/api/folder_path', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    console.log("Success:", data.message);
                } else if (data.error) {
                    console.error("Error:", data.error);
                }
            })
            .catch(error => {
                console.error("Error processing data:", error);
            });
        }
    };

    const ragForm = document.createElement('form');

    const pathLabel = document.createElement('label');
    pathLabel.innerText = "Write the path of local directory you wish to use (ex. C:\\Users\\user\\test):";
    pathLabel.setAttribute('for', 'ragPath');

    const ragPath = document.createElement('input');
    ragPath.type = "text";
    ragPath.name = "ragPath";
    ragPath.id = "ragPath";
    ragPath.style.width = "100%";

    // Create a button for directory selection
    const directoryButton = document.createElement('button');
    directoryButton.type = "button";
    directoryButton.innerText = "Select Directory";
    directoryButton.className = "rag-button";
    directoryButton.id = "selectDirectory";
    directoryButton.onclick = async function() {
        try {
            // Check if the File System Access API is available
            if ('showDirectoryPicker' in window) {
                const dirHandle = await window.showDirectoryPicker();
                // Get directory path or name
                RAGPath = dirHandle;
                ragPath.value = RAGPath.name;
                ragSwitch.disabled = false;
                console.log("Selected directory:", RAGPath);
            } else {
                alert("Your browser doesn't support directory selection. Please enter the path manually.");
            }
        } catch (error) {
            console.error("Error selecting directory:", error);
            if (error.name !== 'AbortError') {
                alert("Error selecting directory: " + error.message);
            }
        }
    };


    // <input type="submit" value="Submit">
    const ragFormSubmit = document.createElement('input');
    ragFormSubmit.type = "submit";
    ragFormSubmit.value = "Submit";
    ragFormSubmit.className = "rag-button";
    ragFormSubmit.id = "ragFormSubmit";

    // on form submit
    ragForm.onsubmit = function(e) {
        e.preventDefault(); // Prevent default form submission
        if(ragPath.value !== '') {
            RAGPath = ragPath.value;
            ragSwitch.disabled = false;
        }
        return false;
    };

    const clearRagButton = document.createElement('input');
    clearRagButton.type = "button";
    clearRagButton.value = "Clear";
    clearRagButton.className = "rag-button";
    clearRagButton.id = "clearRagPath";
    clearRagButton.onclick = function() {
        RAGPath = '';
        ragPath.value = '';
        ragSwitch.disabled = true;
    };

    ragForm.appendChild(pathLabel);
    ragForm.appendChild(ragPath);
    ragForm.appendChild(directoryButton);
    ragForm.appendChild(document.createElement('br')); // Line break
    ragForm.appendChild(ragFormSubmit);
    ragForm.appendChild(clearRagButton);

    //preferredLinksContent.appendChild(createAddLinkButton());
    //preferredLinksContainer.appendChild(preferredLinksContent);
    //settings_window.appendChild(preferredLinksContainer);

    // mcp mode
    settings_window.appendChild(mcpLabel);

    settings_window.appendChild(ragLabel);
    settings_window.appendChild(ragSwitch);
    settings_window.appendChild(ragForm);
    
    settingsIcon.onclick = function (event) {
        event.stopPropagation();
        const rect = settingsIcon.getBoundingClientRect();
        const y = rect.bottom + (isFixedModeRef.value ? 0 : window.scrollY);
        const x = rect.left + (isFixedModeRef.value ? 0 : window.scrollX);
        settings_window.style.top = `${y}px`;
        settings_window.style.left = `${x}px`;
        settings_window.style.display = settings_window.style.display === 'none' ? 'block' : 'none';
        settings_window.style.position = isFixedModeRef.value ? 'fixed' : 'absolute';
        //if (settings_window.style.display === 'block') loadPreferredLinks();
    };

    document.addEventListener('click', function (event) {
        if (
            settings_window.style.display === 'block' &&
            !settings_window.contains(event.target) &&
            !settingsIcon.contains(event.target) &&
            !positionModeIcon.contains(event.target)
        ) {
            settings_window.style.display = 'none';
        }
    });

    return settings_window;
}

export { createSettingsWindow };
