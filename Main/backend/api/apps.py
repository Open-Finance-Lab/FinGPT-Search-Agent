from django.apps import AppConfig
import os
import sys
import logging

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def check_api_keys(self):
        """Check if at least one valid API key is configured."""
        openai_key = os.getenv('OPENAI_API_KEY', '')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')
        deepseek_key = os.getenv('DEEPSEEK_API_KEY', '')
        
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
            logger.error(error_msg)
            raise ImproperlyConfigured("No valid API keys found in .env file")

        logger.info("Configured API keys:")
        if has_openai:
            logger.info("  ✓ OpenAI API key found")
        if has_anthropic:
            logger.info("  ✓ Anthropic API key found")
        if has_deepseek:
            logger.info("  ✓ DeepSeek API key found")
