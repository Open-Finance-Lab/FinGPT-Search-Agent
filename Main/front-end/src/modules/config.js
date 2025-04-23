// config.js

// Available models
const availableModels = ["o3-mini", "gpt-4.5-preview", "deepseek-reasoner"];

// Initialize a single selected model
let selectedModel = "o3-mini";

function getSelectedModel() {
    return selectedModel;
}

export { availableModels, selectedModel, getSelectedModel };