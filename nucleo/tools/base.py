"""Base tool interface for the agent."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Tool(ABC):
    """Base class for all tools."""
    
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize tool with optional configuration.
        
        Args:
            config: Tool-specific configuration
        """
        self.config = config or {}
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Tool execution result
        """
        pass
    
    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Convert tool to Anthropic tool definition.
        
        Returns:
            Anthropic-compatible tool definition
        """
        return {
            'name': self.name,
            'description': self.description,
            'input_schema': {
                'type': 'object',
                'properties': self.parameters,
                'required': [
                    k for k, v in self.parameters.items()
                    if v.get('required', False)
                ]
            }
        }
    
    @property
    def enabled(self) -> bool:
        """Check if tool is enabled in configuration."""
        return self.config.get('enabled', True)
