"""
Model configuration for FinGPT backend.
Central configuration for all supported LLM models.
"""

MODELS_CONFIG = {
    # OpenAI Models
    "o4-mini": {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "supports_rag": True,
        "supports_mcp": True,
        "supports_advanced": True,
        "max_tokens": 128000,
        "description": "GPT-4o Mini - Fast and efficient"
    },
    "gpt-4.5-preview": {
        "provider": "openai", 
        "model_name": "gpt-4-turbo-preview",
        "supports_rag": True,
        "supports_mcp": False,
        "supports_advanced": True,
        "max_tokens": 128000,
        "description": "GPT-4 Turbo Preview - Advanced reasoning"
    },
    "o1-pro": {
        "provider": "openai",
        "model_name": "o1-pro",
        "supports_rag": True,
        "supports_mcp": True,
        "supports_advanced": True,
        "max_tokens": 128000,
        "description": "O1 Pro - Advanced model with enhanced capabilities"
    },
    
    # DeepSeek Models
    "deepseek-reasoner": {
        "provider": "deepseek",
        "model_name": "deepseek-reasoner",
        "supports_rag": True,
        "supports_mcp": True,
        "supports_advanced": True,
        "max_tokens": 128000,
        "description": "DeepSeek R1 - Advanced reasoning model",
        "temperature_range": [0.5, 0.7],
        "recommended_temperature": 0.6
    },
    
    # Anthropic Claude Models
    "claude-3.5": {
        "provider": "anthropic",
        "model_name": "claude-3-5-sonnet-latest",
        "supports_rag": True,
        "supports_mcp": True,
        "supports_advanced": True,
        "max_tokens": 200000,
        "description": "Claude 3.5 Sonnet - Balanced performance"
    },
    "claude-3.7": {
        "provider": "anthropic",
        "model_name": "claude-3-opus-latest",
        "supports_rag": True,
        "supports_mcp": True,
        "supports_advanced": True,
        "max_tokens": 200000,
        "description": "Claude 3 Opus - High performance"
    },
    "claude-4": {
        "provider": "anthropic",
        "model_name": "claude-4-opus-latest",
        "supports_rag": True,
        "supports_mcp": True,
        "supports_advanced": True,
        "max_tokens": 200000,
        "description": "Claude 4 Opus - Latest and most capable"
    }
}

# Provider configurations
PROVIDER_CONFIGS = {
    "openai": {
        "base_url": None,  # Uses default OpenAI URL
        "env_key": "OPENAI_API_KEY",
        "client_class": "OpenAI"
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "env_key": "DEEPSEEK_API_KEY",
        "client_class": "OpenAI"  # DeepSeek is OpenAI-compatible
    },
    "anthropic": {
        "base_url": None,  # Uses default Anthropic URL
        "env_key": "ANTHROPIC_API_KEY",
        "client_class": "Anthropic"
    }
}

def get_model_config(model_id: str) -> dict:
    """Get configuration for a specific model."""
    return MODELS_CONFIG.get(model_id, None)

def get_provider_config(provider: str) -> dict:
    """Get configuration for a specific provider."""
    return PROVIDER_CONFIGS.get(provider, None)

def get_available_models() -> list[str]:
    """Get list of all available model IDs."""
    return list(MODELS_CONFIG.keys())

def get_models_by_provider(provider: str) -> list[str]:
    """Get list of model IDs for a specific provider."""
    return [
        model_id 
        for model_id, config in MODELS_CONFIG.items() 
        if config["provider"] == provider
    ]

def validate_model_support(model_id: str, feature: str) -> bool:
    """Check if a model supports a specific feature (rag, mcp, advanced)."""
    config = get_model_config(model_id)
    if not config:
        return False
    return config.get(f"supports_{feature}", False)