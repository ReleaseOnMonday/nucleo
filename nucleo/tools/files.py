"""File operations tool."""

from pathlib import Path
from typing import Any, Dict

from .base import Tool


class FilesTool(Tool):
    """File operations (read, write, list)."""

    name = "files"
    description = "Read, write, and list files in the workspace"
    parameters = {
        "operation": {
            "type": "string",
            "description": "Operation to perform: read, write, list, delete",
            "enum": ["read", "write", "list", "delete"],
            "required": True,
        },
        "path": {
            "type": "string",
            "description": "File or directory path (relative to workspace)",
            "required": True,
        },
        "content": {
            "type": "string",
            "description": "Content to write (for write operation)",
            "required": False,
        },
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize files tool.

        Args:
            config: Tool configuration
        """
        super().__init__(config)
        self.workspace = Path(config.get("workspace", "./workspace"))
        self.workspace.mkdir(parents=True, exist_ok=True)

    async def execute(
        self, operation: str, path: str, content: str = None, **kwargs
    ) -> Dict[str, Any]:
        """Execute file operation.

        Args:
            operation: Operation type
            path: File path
            content: Content for write operation

        Returns:
            Operation result
        """
        # Sanitize path
        full_path = self._get_safe_path(path)
        if not full_path:
            return {"success": False, "error": "Invalid path (outside workspace)"}

        try:
            if operation == "read":
                return await self._read(full_path)
            elif operation == "write":
                return await self._write(full_path, content)
            elif operation == "list":
                return await self._list(full_path)
            elif operation == "delete":
                return await self._delete(full_path)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_safe_path(self, path: str) -> Path:
        """Get safe path within workspace.

        Args:
            path: User-provided path

        Returns:
            Safe absolute path or None
        """
        full_path = (self.workspace / path).resolve()

        # Ensure path is within workspace
        try:
            full_path.relative_to(self.workspace)
            return full_path
        except ValueError:
            return None

    async def _read(self, path: Path) -> Dict[str, Any]:
        """Read file content.

        Args:
            path: File path

        Returns:
            File content
        """
        if not path.exists():
            return {"success": False, "error": "File not found"}

        if not path.is_file():
            return {"success": False, "error": "Path is not a file"}

        # Check file size
        max_size = self.config.get("max_file_size_mb", 10) * 1024 * 1024
        if path.stat().st_size > max_size:
            return {
                "success": False,
                "error": f"File too large (max {max_size / 1024 / 1024}MB)",
            }

        content = path.read_text(encoding="utf-8")

        return {"success": True, "content": content, "size": path.stat().st_size}

    async def _write(self, path: Path, content: str) -> Dict[str, Any]:
        """Write content to file.

        Args:
            path: File path
            content: Content to write

        Returns:
            Write result
        """
        if content is None:
            return {"success": False, "error": "No content provided"}

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "path": str(path.relative_to(self.workspace)),
            "size": len(content),
        }

    async def _list(self, path: Path) -> Dict[str, Any]:
        """List directory contents.

        Args:
            path: Directory path

        Returns:
            Directory listing
        """
        if not path.exists():
            return {"success": False, "error": "Path not found"}

        if path.is_file():
            # Return single file info
            return {
                "success": True,
                "files": [
                    {"name": path.name, "size": path.stat().st_size, "type": "file"}
                ],
            }

        # List directory
        items = []
        for item in path.iterdir():
            items.append(
                {
                    "name": item.name,
                    "size": item.stat().st_size if item.is_file() else 0,
                    "type": "file" if item.is_file() else "directory",
                }
            )

        return {"success": True, "files": items, "count": len(items)}

    async def _delete(self, path: Path) -> Dict[str, Any]:
        """Delete file or directory.

        Args:
            path: Path to delete

        Returns:
            Delete result
        """
        if not path.exists():
            return {"success": False, "error": "Path not found"}

        if path.is_file():
            path.unlink()
        else:
            import shutil

            shutil.rmtree(path)

        return {"success": True, "deleted": str(path.relative_to(self.workspace))}
