"""
Preferred Links Manager
Handles storage and retrieval of user-defined preferred links using JSON file storage.
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from threading import Lock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PreferredLinksManager:
    """Manages preferred links with JSON file storage."""

    def __init__(self, storage_path: str = None):
        """
        Initialize the manager with a storage path.

        Args:
            storage_path: Path to the JSON storage file.
                         Defaults to backend/data/preferred_links.json
        """
        if storage_path is None:
            # Default path: backend/data/preferred_links.json
            backend_dir = Path(__file__).resolve().parent.parent
            self.storage_path = backend_dir / 'data' / 'preferred_links.json'
        else:
            self.storage_path = Path(storage_path)

        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread lock for file operations
        self.lock = Lock()

        # Initialize file if it doesn't exist
        if not self.storage_path.exists():
            self._init_storage()

    def _init_storage(self):
        """Initialize the storage file with default structure."""
        default_data = {
            "version": "1.0",
            "preferred_links": [],
            "metadata": {
                "last_updated": None,
                "total_links": 0
            }
        }
        self._write_data(default_data)
        logging.info(f"Initialized preferred links storage at {self.storage_path}")

    def _read_data(self) -> Dict[Any, Any]:
        """Read data from the JSON file."""
        try:
            with self.lock:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Error reading preferred links file: {e}")
            self._init_storage()
            return self._read_data()

    def _write_data(self, data: Dict[Any, Any]):
        """Write data to the JSON file."""
        try:
            with self.lock:
                with open(self.storage_path, 'w') as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Error writing to preferred links file: {e}")
            raise

    def get_links(self) -> List[str]:
        """
        Get all preferred links.

        Returns:
            List of preferred link URLs
        """
        data = self._read_data()
        links = data.get('preferred_links', [])
        logging.info(f"Retrieved {len(links)} preferred links from storage")
        return links

    def set_links(self, links: List[str]):
        """
        Replace all preferred links with a new list.

        Args:
            links: List of URLs to set as preferred links
        """
        data = self._read_data()
        # Remove duplicates while preserving order
        unique_links = []
        seen = set()
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)

        data['preferred_links'] = unique_links
        data['metadata']['total_links'] = len(unique_links)

        from datetime import datetime
        data['metadata']['last_updated'] = datetime.now().isoformat()

        self._write_data(data)
        logging.info(f"Updated preferred links: {len(unique_links)} links saved")

    def add_link(self, link: str) -> bool:
        """
        Add a single link to preferred links.

        Args:
            link: URL to add

        Returns:
            True if added, False if already exists
        """
        links = self.get_links()
        if link not in links:
            links.append(link)
            self.set_links(links)
            return True
        return False

    def remove_link(self, link: str) -> bool:
        """
        Remove a link from preferred links.

        Args:
            link: URL to remove

        Returns:
            True if removed, False if not found
        """
        links = self.get_links()
        if link in links:
            links.remove(link)
            self.set_links(links)
            return True
        return False

    def clear_links(self):
        """Clear all preferred links."""
        self.set_links([])
        logging.info("Cleared all preferred links")

    def sync_from_frontend(self, frontend_links: List[str]):
        """
        Sync preferred links from frontend.

        Args:
            frontend_links: List of URLs from frontend
        """
        if frontend_links:
            self.set_links(frontend_links)
            logging.info(f"Synced {len(frontend_links)} links from frontend")

    def get_or_sync(self, frontend_links: List[str] = None) -> List[str]:
        """
        Get preferred links, optionally syncing from frontend first.

        Args:
            frontend_links: Optional list of URLs from frontend to sync

        Returns:
            List of preferred link URLs
        """
        if frontend_links is not None and len(frontend_links) > 0:
            self.sync_from_frontend(frontend_links)
            return frontend_links
        return self.get_links()


# Global instance
_manager_instance = None

def get_manager() -> PreferredLinksManager:
    """Get the global PreferredLinksManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PreferredLinksManager()
    return _manager_instance