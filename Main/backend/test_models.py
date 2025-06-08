#!/usr/bin/env python3
"""
Test script to verify model configuration and basic functionality.
Run this script to test the refactored model system.
"""

import os
import sys
sys.path.append('datascraper')

from datascraper.models_config import (
    get_available_models, 
    get_model_config, 
    get_models_by_provider,
    validate_model_support
)

def test_models_config():
    """Test the models configuration system."""
    print("=== Testing Models Configuration ===")
    
    # Test available models
    models = get_available_models()
    print(f"Available models: {models}")
    
    # Test each model configuration
    for model_id in models:
        config = get_model_config(model_id)
        print(f"\n{model_id}:")
        print(f"  Provider: {config['provider']}")
        print(f"  Model Name: {config['model_name']}")
        print(f"  Supports RAG: {config['supports_rag']}")
        print(f"  Supports MCP: {config['supports_mcp']}")
        print(f"  Supports Advanced: {config['supports_advanced']}")
    
    # Test provider grouping
    print("\n=== Models by Provider ===")
    providers = set(get_model_config(m)['provider'] for m in models)
    for provider in providers:
        provider_models = get_models_by_provider(provider)
        print(f"{provider}: {provider_models}")
    
    # Test feature validation
    print("\n=== Feature Support ===")
    test_model = models[0] if models else None
    if test_model:
        print(f"Testing {test_model}:")
        print(f"  RAG: {validate_model_support(test_model, 'rag')}")
        print(f"  MCP: {validate_model_support(test_model, 'mcp')}")
        print(f"  Advanced: {validate_model_support(test_model, 'advanced')}")

def test_api_keys():
    """Test API key availability."""
    print("\n=== Testing API Keys ===")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    keys = {
        'OpenAI': os.getenv('OPENAI_API_KEY'),
        'DeepSeek': os.getenv('DEEPSEEK_API_KEY'),
        'Anthropic': os.getenv('ANTHROPIC_API_KEY')
    }
    
    for provider, key in keys.items():
        status = "✓ Available" if key and key.strip() else "✗ Missing"
        print(f"{provider}: {status}")

if __name__ == "__main__":
    try:
        test_models_config()
        test_api_keys()
        print("\n=== Configuration Test Complete ===")
    except Exception as e:
        print(f"Error during testing: {e}")
        sys.exit(1)