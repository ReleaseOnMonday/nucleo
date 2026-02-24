"""Bash command execution tool."""

import asyncio
from typing import Any, Dict

from .base import Tool


class BashTool(Tool):
    """Execute bash commands safely."""

    name = "bash"
    description = "Execute bash commands in a sandboxed environment"
    parameters = {
        "command": {
            "type": "string",
            "description": "The bash command to execute",
            "required": True,
        }
    }

    async def execute(self, command: str, **kwargs) -> Dict[str, Any]:
        """Execute bash command.

        Args:
            command: Bash command to execute

        Returns:
            Command output and exit code
        """
        # Check if command is allowed
        if not self._is_allowed(command):
            return {
                "success": False,
                "error": f"Command not allowed: {command.split()[0]}",
            }

        try:
            # Run command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0,  # 30 second timeout
            )

            # Limit output size
            max_length = self.config.get("max_output_length", 10000)
            stdout_str = stdout.decode("utf-8", errors="replace")[:max_length]
            stderr_str = stderr.decode("utf-8", errors="replace")[:max_length]

            return {
                "success": process.returncode == 0,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": process.returncode,
            }

        except asyncio.TimeoutError:
            return {"success": False, "error": "Command timed out after 30 seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _is_allowed(self, command: str) -> bool:
        """Check if command is in allowed list.

        Args:
            command: Command to check

        Returns:
            True if allowed, False otherwise
        """
        allowed = self.config.get("allowed_commands", [])

        # If no allow list, allow all (dangerous!)
        if not allowed:
            return True

        # Check if base command is allowed
        base_cmd = command.split()[0]
        return base_cmd in allowed or "*" in allowed
