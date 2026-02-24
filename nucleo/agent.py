"""Core agent with tool orchestration and conversation management."""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

from .config import Config
from .llm import LLMClient
from .tools import BashTool, FilesTool, SearchTool, Tool

# Import channel types (optional, only if channels module is available)
try:
    from .channels.bus import MessageBus
    from .channels.message import OutboundMessage
except ImportError:
    MessageBus = None
    OutboundMessage = None


class Agent:
    """Lightweight AI agent with tool support."""
    
    def __init__(self, config: Optional[Config] = None, bus: Optional['MessageBus'] = None):
        """Initialize agent.
        
        Args:
            config: Configuration object
            bus: Optional message bus for channel communication
        """
        if config is None:
            config = Config().load()
        
        self.config = config
        self.llm = LLMClient(config.data)
        self.tools: Dict[str, Tool] = {}
        self.history: List[Dict[str, str]] = []
        self.bus = bus
        self._current_metadata: Optional[Dict[str, Any]] = None
        
        # Initialize tools
        self._init_tools()
    
    def _init_tools(self):
        """Initialize available tools."""
        tools_config = self.config.get('tools', {})
        
        # Bash tool
        if tools_config.get('bash', {}).get('enabled', False):
            self.tools['bash'] = BashTool(tools_config.get('bash', {}))
        
        # Search tool
        if tools_config.get('search', {}).get('enabled', False):
            self.tools['search'] = SearchTool(tools_config.get('search', {}))
        
        # Files tool
        if tools_config.get('files', {}).get('enabled', True):
            self.tools['files'] = FilesTool(tools_config.get('files', {}))
    
    async def chat(self, message: str, stream: bool = True, metadata: Optional[Dict[str, Any]] = None) -> AsyncIterator[str]:
        """Chat with the agent.
        
        Args:
            message: User message
            stream: Whether to stream response
            metadata: Optional metadata from channel (sender_id, chat_id, platform, etc.)
            
        Yields:
            Response chunks
        """
        # Store current message metadata for potential channel response routing
        self._current_metadata = metadata
        
        # Add user message to history
        self.history.append({
            'role': 'user',
            'content': message
        })
        
        # Prepare messages with system prompt
        messages = self._prepare_messages()
        
        # Get tool definitions
        tool_defs = [tool.to_anthropic_tool() for tool in self.tools.values()]
        
        # Initial LLM call
        response_content = ''
        tool_calls = []
        
        # Stream or complete response
        async for chunk in self.llm.chat_stream(messages, tool_defs if tool_defs else None):
            if chunk['type'] == 'text':
                response_content += chunk['content']
                if stream:
                    yield chunk['content']
            elif chunk['type'] == 'tool_use':
                tool_calls.append(chunk)
        
        # If no tool calls, we're done
        if not tool_calls:
            self.history.append({
                'role': 'assistant',
                'content': response_content
            })
            return
        
        # Execute tools and continue conversation
        max_iterations = self.config.get('agent.max_tool_iterations', 10)
        
        for iteration in range(max_iterations):
            # Execute all tool calls
            tool_results = []
            
            for tool_call in tool_calls:
                result = await self._execute_tool(tool_call)
                tool_results.append(result)
                
                # Stream tool execution info
                if stream:
                    yield f"\n[Tool: {tool_call['name']}]\n"
            
            # Add assistant message with tool use
            self.history.append({
                'role': 'assistant',
                'content': [
                    {'type': 'text', 'text': response_content}
                ] + [
                    {
                        'type': 'tool_use',
                        'id': tc['id'],
                        'name': tc['name'],
                        'input': tc['input']
                    }
                    for tc in tool_calls
                ]
            })
            
            # Add tool results
            self.history.append({
                'role': 'user',
                'content': [
                    {
                        'type': 'tool_result',
                        'tool_use_id': result['tool_use_id'],
                        'content': json.dumps(result['content'])
                    }
                    for result in tool_results
                ]
            })
            
            # Continue conversation
            messages = self._prepare_messages()
            response_content = ''
            tool_calls = []
            
            async for chunk in self.llm.chat_stream(messages, tool_defs):
                if chunk['type'] == 'text':
                    response_content += chunk['content']
                    if stream:
                        yield chunk['content']
                elif chunk['type'] == 'tool_use':
                    tool_calls.append(chunk)
            
            # If no more tool calls, we're done
            if not tool_calls:
                self.history.append({
                    'role': 'assistant',
                    'content': response_content
                })
                break
        
        # Manage history size
        self._trim_history()
    
    async def _execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call.
        
        Args:
            tool_call: Tool call information
            
        Returns:
            Tool execution result
        """
        tool_name = tool_call['name']
        tool_input = tool_call['input']
        
        if tool_name not in self.tools:
            return {
                'tool_use_id': tool_call['id'],
                'content': {'error': f'Tool not found: {tool_name}'}
            }
        
        try:
            result = await self.tools[tool_name].execute(**tool_input)
            return {
                'tool_use_id': tool_call['id'],
                'content': result
            }
        except Exception as e:
            return {
                'tool_use_id': tool_call['id'],
                'content': {'error': str(e)}
            }
    
    def _prepare_messages(self) -> List[Dict[str, Any]]:
        """Prepare messages for LLM.
        
        Returns:
            Messages with system prompt
        """
        system_prompt = self.config.get(
            'agent.system_prompt',
            'You are a helpful AI assistant. Be concise and practical.'
        )
        
        messages = [
            {'role': 'system', 'content': system_prompt}
        ] + self.history
        
        return messages
    
    def _trim_history(self):
        """Trim conversation history to manage memory."""
        max_messages = self.config.get('memory.max_history_messages', 50)
        
        if len(self.history) > max_messages:
            # Keep system message and most recent messages
            self.history = self.history[-max_messages:]
    
    def reset(self):
        """Reset conversation history."""
        self.history = []
        self._current_metadata = None
    
    async def send_to_channel(self, content: str, media: Optional[List[str]] = None) -> None:
        """Send a message back to the channel that sent the current message.
        
        This allows the agent to proactively send messages to channels
        (e.g., notifications, command results).
        
        Args:
            content: Message content
            media: Optional list of file paths to send
            
        Raises:
            RuntimeError: If no channel bus available or no current message metadata
        """
        if not self.bus or not OutboundMessage:
            raise RuntimeError("Channel bus not available")
        
        if not self._current_metadata:
            raise RuntimeError("No current message metadata (not called from channel)")
        
        metadata = self._current_metadata
        
        # Create outbound message and publish
        outbound = OutboundMessage(
            channel=metadata.get('platform', ''),
            chat_id=metadata.get('chat_id', ''),
            content=content,
            media=media or [],
            metadata={}
        )
        
        await self.bus.publish_outbound(outbound)
