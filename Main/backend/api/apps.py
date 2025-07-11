from django.apps import AppConfig
import os
import sys


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    # def ready(self):
    #     """
    #     Check for API keys when the Django app is ready.
    #     This runs before the server starts serving requests.
    #     """
    #     # Only check when running the development server
    #     if 'runserver' in sys.argv:
    #         self.check_api_keys()
    
    def check_api_keys(self):
        """Check if at least one valid API key is configured."""
        # Get API keys from environment
        openai_key = os.getenv('OPENAI_API_KEY', '')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')
        deepseek_key = os.getenv('DEEPSEEK_API_KEY', '')
        
        # Check if any real API key is present (not empty and not placeholder)
        has_openai = openai_key and 'your-' not in openai_key.lower() and len(openai_key) > 20
        has_anthropic = anthropic_key and 'your-' not in anthropic_key.lower() and len(anthropic_key) > 20
        has_deepseek = deepseek_key and 'your-' not in deepseek_key.lower() and len(deepseek_key) > 20
        
        if not (has_openai or has_anthropic or has_deepseek):
            from django.core.exceptions import ImproperlyConfigured
            error_msg = """
========================================
ERROR: No valid API keys configured!
========================================

FinGPT requires at least one API key to function.

Please edit the .env file and add at least one of:
  - OPENAI_API_KEY=your-actual-key
  - ANTHROPIC_API_KEY=your-actual-key  
  - DEEPSEEK_API_KEY=your-actual-key

Note: MCP features require an OpenAI API key.

You can get API keys from:
  - OpenAI: https://platform.openai.com/api-keys
  - Anthropic: https://console.anthropic.com/
  - DeepSeek: https://platform.deepseek.com/

========================================
"""
            print(error_msg)
            # Use Django's ImproperlyConfigured to stop the server
            raise ImproperlyConfigured("No valid API keys found in .env file")
        
        # Show which API keys are configured
        print("\nConfigured API keys:")
        if has_openai:
            print("  ✓ OpenAI API key found")
        if has_anthropic:
            print("  ✓ Anthropic API key found")
        if has_deepseek:
            print("  ✓ DeepSeek API key found")
        print()