"""
Prompt builder for the FinGPT search agent.

Loads prompt files from Main/backend/prompts/ and assembles the final
system prompt based on the user's current site context.

Assembly rule:
    final = core.md + (matched site skill OR default_site.md) + time context + system override
"""

import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PromptBuilder:
    """Assembles agent system prompts from markdown files."""

    def __init__(self, prompts_dir: Optional[str] = None):
        self._dir = Path(prompts_dir) if prompts_dir else _DEFAULT_PROMPTS_DIR
        self._cache: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        current_url: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_timezone: Optional[str] = None,
        user_time: Optional[str] = None,
    ) -> str:
        """Return the fully assembled system prompt."""

        parts: list[str] = []

        # 1. Core (always included)
        parts.append(self._load_prompt("core.md"))

        # 2. Site skill OR default — mutually exclusive
        domain = self._extract_domain(current_url)
        site_prompt = self._match_site(domain) if domain else None

        if site_prompt:
            parts.append(site_prompt)
            logger.info("[PromptBuilder] Matched site skill for domain: %s", domain)
        else:
            parts.append(self._load_prompt("default_site.md"))
            logger.info("[PromptBuilder] Using default site prompt (domain: %s)", domain or "none")

        # User context block (URL + domain)
        if current_url and domain:
            parts.append(
                f"USER CONTEXT:\n- Current URL: {current_url}\n- Active Domain: {domain}\n\n"
                f"IMPORTANT: You may ONLY scrape/interact with URLs within {domain}. "
                "For external domains, decline and suggest Research mode."
            )

        # 3. Time context
        time_block = self._build_time_context(user_timezone, user_time)
        if time_block:
            parts.append(time_block)

        # 4. System override
        if system_prompt:
            parts.append(f"SYSTEM OVERRIDE:\n{system_prompt}")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_prompt(self, filename: str) -> str:
        """Load and cache a prompt file from the prompts directory."""
        if filename in self._cache:
            return self._cache[filename]

        path = self._dir / filename
        if not path.exists():
            logger.warning("[PromptBuilder] Prompt file not found: %s", path)
            return ""

        text = path.read_text(encoding="utf-8").strip()
        self._cache[filename] = text
        return text

    def _match_site(self, domain: str) -> Optional[str]:
        """Scan prompts/sites/ for a file whose name (minus .md) matches the domain via endswith."""
        sites_dir = self._dir / "sites"
        if not sites_dir.is_dir():
            return None

        for md_file in sites_dir.glob("*.md"):
            site_key = md_file.stem  # e.g. "finance.yahoo.com"
            if domain.endswith(site_key):
                return self._load_prompt(f"sites/{md_file.name}")

        return None

    @staticmethod
    def _extract_domain(url: Optional[str]) -> Optional[str]:
        """Extract and normalise the domain from a URL."""
        if not url:
            return None
        parsed = urlparse(url)
        domain = (parsed.netloc or "").lower()
        return domain or None

    @staticmethod
    def _build_time_context(
        user_timezone: Optional[str], user_time: Optional[str]
    ) -> Optional[str]:
        """Build a time-context string, or return None."""
        if not user_timezone and not user_time:
            return None

        info_parts: list[str] = []

        if user_timezone and user_time:
            try:
                from datetime import datetime
                import pytz

                utc_time = datetime.fromisoformat(user_time.replace("Z", "+00:00"))
                user_tz = pytz.timezone(user_timezone)
                local_time = utc_time.astimezone(user_tz)

                info_parts.append(f"User's timezone: {user_timezone}")
                info_parts.append(
                    f"Current local time for user: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            except Exception as exc:
                logger.warning("Error formatting time info: %s", exc)
                if user_timezone:
                    info_parts.append(f"User's timezone: {user_timezone}")
        elif user_timezone:
            info_parts.append(f"User's timezone: {user_timezone}")

        if info_parts:
            return f"[TIME CONTEXT]: {' | '.join(info_parts)}"
        return None
