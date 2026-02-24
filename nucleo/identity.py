"""Identity system for consistent agent personality and behavior."""

from pathlib import Path
from typing import Optional


class IdentityManager:
    """Manages agent identity across channels and conversations."""

    def __init__(self, workspace_path: Optional[str] = None):
        """Initialize identity manager.

        Args:
            workspace_path: Path to workspace directory containing identity files
        """
        if workspace_path is None:
            workspace_path = str(Path.cwd() / "workspace")

        self.workspace_path = Path(workspace_path)
        self.identity_file = self.workspace_path / "IDENTITY.md"
        self.soul_file = self.workspace_path / "SOUL.md"
        self.user_file = self.workspace_path / "USER.md"

        # Cache loaded identity
        self._identity_cache: Optional[str] = None
        self._soul_cache: Optional[str] = None
        self._user_cache: Optional[str] = None

    def get_identity(self, use_cache: bool = True) -> str:
        """Get agent identity (who are you?).

        Args:
            use_cache: Use cached version if available

        Returns:
            Identity content
        """
        if use_cache and self._identity_cache is not None:
            return self._identity_cache

        if not self.identity_file.exists():
            return "You are Nucleo, a helpful AI assistant.\n"

        try:
            content = self.identity_file.read_text()
            if use_cache:
                self._identity_cache = content
            return content
        except Exception:
            return "You are Nucleo, a helpful AI assistant.\n"

    def get_soul(self, use_cache: bool = True) -> str:
        """Get agent personality and values (soul).

        Args:
            use_cache: Use cached version if available

        Returns:
            Soul/personality content
        """
        if use_cache and self._soul_cache is not None:
            return self._soul_cache

        if not self.soul_file.exists():
            return ""

        try:
            content = self.soul_file.read_text()
            if use_cache:
                self._soul_cache = content
            return content
        except Exception:
            return ""

    def get_user_context(self, use_cache: bool = True) -> str:
        """Get user profile and context information.

        Args:
            use_cache: Use cached version if available

        Returns:
            User context content
        """
        if use_cache and self._user_cache is not None:
            return self._user_cache

        if not self.user_file.exists():
            return ""

        try:
            content = self.user_file.read_text()
            if use_cache:
                self._user_cache = content
            return content
        except Exception:
            return ""

    def get_full_identity_context(self) -> str:
        """Get complete identity context for injecting into system prompt.

        Combines identity, soul, and user context into a cohesive prompt injection.

        Returns:
            Full identity context
        """
        parts = []

        # Add identity section
        identity = self.get_identity()
        if identity:
            parts.append(identity)

        # Add soul section
        soul = self.get_soul()
        if soul:
            parts.append(soul)

        # Add user context
        user_ctx = self.get_user_context()
        if user_ctx:
            parts.append(user_ctx)

        return "\n\n".join(parts) if parts else ""

    def get_system_prompt_injection(self) -> str:
        """Get system prompt injection suitable for LLM system roles.

        Returns:
            System prompt injection
        """
        context = self.get_full_identity_context()

        if not context:
            return ""

        return f"""
# Agent Identity and Context

{context}

---
Use this identity to guide your responses. Be consistent with these values and personality across all interactions.
"""

    def reload_cache(self):
        """Reload all cached identity components."""
        self._identity_cache = None
        self._soul_cache = None
        self._user_cache = None

    def has_identity_files(self) -> bool:
        """Check if identity files exist.

        Returns:
            True if at least one identity file exists
        """
        return (
            self.identity_file.exists()
            or self.soul_file.exists()
            or self.user_file.exists()
        )
