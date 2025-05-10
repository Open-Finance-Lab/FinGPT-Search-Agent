from django.apps import AppConfig


class ChatServerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat_server_app'

    def ready(self):
        """
        Import and initialize the MCP tools when the Django app is ready.
        This ensures your MCP tools are loaded when Django starts.
        """
        # Import MCP tools module
        from datascraper.mcp import mcp_tools
