// config.js

// Available models
const availableModels = ["o4-mini", "o1-pro", "deepseek-reasoner", "claude-3.5", "claude-3.7", "claude-4"];

// Initialize a single selected model
let selectedModel = "o4-mini";

function getSelectedModel() {
    return selectedModel;
}

function setSelectedModel(model) {
    selectedModel = model;
}

export { availableModels, selectedModel, getSelectedModel, setSelectedModel };