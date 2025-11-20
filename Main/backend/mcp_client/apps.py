import logging
import asyncio
import threading
from django.apps import AppConfig

logger = logging.getLogger(__name__)

# Global MCP Manager instance that persists across requests
_global_mcp_manager = None
_global_mcp_lock = threading.Lock()
_initialized = False  # Process-level flag to prevent double initialization

def get_global_mcp_manager():
    """Get the global MCP manager instance"""
    return _global_mcp_manager

def set_global_mcp_manager(manager):
    """Set the global MCP manager instance"""
    global _global_mcp_manager
    _global_mcp_manager = manager

class MCPClientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mcp_client'

    def ready(self):
        """
        Initialize global MCP manager on Django startup.
        This ensures all MCP connections are ready when the backend starts.
        """
        global _initialized

        # Prevent double initialization in the same process
        if _initialized:
            print("[MCP DEBUG] MCP already initialized in this process, skipping")
            return

        import os
        import sys

        # In development with auto-reload, only run in the child process
        # In production (gunicorn), RUN_MAIN won't be set, so we'll initialize
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            print("[MCP DEBUG] Skipping MCP init in Django autoreload parent process")
            return

        _initialized = True

        # Detect if we're running in a gunicorn worker (for quieter logging on worker 2+)
        worker_id = os.getenv('GUNICORN_WORKER_ID')
        verbose_marker_path = os.getenv('MCP_VERBOSE_MARKER_PATH', '/tmp/mcp_verbose_worker')
        force_verbose = os.getenv('MCP_DEBUG_FORCE_VERBOSE') == '1'
        force_quiet = os.getenv('MCP_DEBUG_FORCE_QUIET') == '1'
        configured_workers = {
            w.strip() for w in os.getenv('MCP_VERBOSE_WORKERS', '1').split(',') if w.strip()
        }

        def claim_verbose_slot() -> bool:
            """Allow only the first worker without an ID to log verbosely."""
            try:
                fd = os.open(verbose_marker_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return True
            except FileExistsError:
                return False

        if force_quiet:
            is_verbose = False
        elif force_verbose:
            is_verbose = True
        elif worker_id:
            is_verbose = worker_id in configured_workers
        else:
            is_verbose = claim_verbose_slot()

        if is_verbose:
            print("\n" + "="*60)
            print("[MCP DEBUG] --- MCP Client App Starting ---")
            print(f"[MCP DEBUG] Process ID: {os.getpid()}")
            print("="*60)
        else:
            worker_label = worker_id if worker_id is not None else str(os.getpid())
            print(f"[MCP DEBUG] Worker {worker_label} initializing MCP (quiet mode)...")

        from .mcp_manager import MCPClientManager

        async def initialize_global_manager(verbose=True):
            """Initialize and maintain the global MCP manager"""
            global _global_mcp_manager

            def log(msg):
                """Conditional logging based on verbose flag"""
                if verbose:
                    print(msg)

            try:
                log("[MCP DEBUG] Creating MCP Client Manager...")
                manager = MCPClientManager(verbose=verbose)

                log("[MCP DEBUG] Loading MCP server configuration...")
                config = await manager.load_config()
                server_count = len(config.get("mcpServers", {}))
                log(f"[MCP DEBUG] Found {server_count} MCP servers in config")

                if server_count > 0:
                    log("[MCP DEBUG] Initiating connections to MCP servers...")
                    await manager.connect_to_servers()

                    tools = await manager.get_all_tools()
                    if verbose:
                        print("-" * 60)
                        print(f"[MCP DEBUG] Successfully connected to all MCP servers!")
                        print(f"[MCP DEBUG] Total tools discovered: {len(tools)}")
                        print("-" * 60)

                    # Store the manager globally
                    with _global_mcp_lock:
                        set_global_mcp_manager(manager)

                    if verbose:
                        print("-" * 60)
                        print("[MCP DEBUG] Global MCP Manager initialized and ready!")
                        print("[MCP DEBUG] MCP connections will persist for process lifetime")
                        print("=" * 60 + "\n")
                    else:
                        print(f"[MCP DEBUG] MCP ready ({len(tools)} tools)")
                else:
                    log("[MCP DEBUG] No MCP servers configured. MCP is disabled.")
                    if verbose:
                        print("=" * 60 + "\n")

            except Exception as e:
                if verbose:
                    print("=" * 60)
                    print(f"[MCP DEBUG] Failed to initialize global MCP manager: {e}")
                    print("=" * 60 + "\n")
                else:
                    print(f"[MCP DEBUG] MCP init failed: {e}")
                logger.error(f"MCP initialization failed: {e}", exc_info=True)

        # Run the async initialization in a background thread
        def run_async_init():
            """Run MCP initialization and keep event loop alive for async operations"""
            try:
                if is_verbose:
                    print("[MCP DEBUG] Starting async initialization in background thread...")

                # Create and set event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Initialize MCP manager
                loop.run_until_complete(initialize_global_manager(verbose=is_verbose))

                # Keep the loop running to maintain MCP sessions
                # MCP uses stdio/SSE transports which need an active event loop
                if is_verbose:
                    print("[MCP DEBUG] Event loop now running to maintain connections...")

                # Run forever - the daemon thread will exit when Django shuts down
                loop.run_forever()

            except Exception as e:
                print(f"[MCP DEBUG] ✗ Error in MCP initialization thread: {e}")
                logger.error(f"Error in MCP initialization thread: {e}", exc_info=True)
            finally:
                # Cleanup when thread exits
                try:
                    loop.close()
                except Exception as e:
                    logger.error(f"Error closing event loop: {e}")

        thread = threading.Thread(target=run_async_init, name="MCPManagerThread", daemon=True)
        thread.start()

        if is_verbose:
            print("[MCP DEBUG] Background initialization thread started")
            print("[MCP DEBUG] Waiting for MCP initialization to complete...")
            print("")
