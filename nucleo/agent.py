"""Core agent with tool orchestration and conversation management."""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

from .config import Config
from .llm import LLMClient
from .tools import BashTool, FilesTool, SearchTool, Tool
from .memory import MemoryManager
from .identity import IdentityManager

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
        self._current_user_id: Optional[str] = None
        
        # Initialize memory system if enabled
        memory_enabled = self.config.get('memory.enabled', True)
        self.memory: Optional[MemoryManager] = None
        if memory_enabled:
            memory_db_path = self.config.get('memory.db_path', None)
            self.memory = MemoryManager(db_path=memory_db_path)
        
        # Initialize identity system if enabled
        identity_enabled = self.config.get('identity.enabled', True)
        self.identity: Optional[IdentityManager] = None
        if identity_enabled:
            workspace_path = self.config.get('identity.workspace_path', None)
            self.identity = IdentityManager(workspace_path=workspace_path)
        
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
        
        # Extract or derive user ID
        if metadata:
            # Try sender_id, user_id, or platform_platform_id format
            self._current_user_id = metadata.get('sender_id') or metadata.get('user_id') or \
                                    f"{metadata.get('platform', 'unknown')}:{metadata.get('chat_id', 'unknown')}"
        
        # Save incoming message to memory if enabled
        if self.memory and self._current_user_id:
            tags = [metadata.get('platform', 'chat')] if metadata else ['chat']
            self.memory.save_memory(self._current_user_id, message, tags=tags, importance=1)
        
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
        
        # Save response to memory if enabled
        if self.memory and self._current_user_id and response_content:
            self.memory.save_memory(self._current_user_id, response_content, tags=['response'], importance=1)
        
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
            Messages with system prompt, identity context, and memory
        """
        system_prompt = self.config.get(
            'agent.system_prompt',
            'You are a helpful AI assistant. Be concise and practical.'
        )
        
        # Add identity context if available
        identity_context = ""
        if self.identity:
            identity_ctx = self.identity.get_system_prompt_injection()
            if identity_ctx:
                identity_context = identity_ctx + "\n\n"
        
        # Add memory context if available
        memory_context = ""
        if self.memory and self._current_user_id:
            # Get recent memories and relevant memories
            recent_memories = self.memory.get_user_memories(self._current_user_id, limit=3)
            
            if recent_memories:
                memory_context = "[Previous Conversation Context]\n"
                for mem in recent_memories:
                    memory_context += f"- {mem['content']}\n"
                memory_context += "\n"
        
        # Combine all context
        full_system_prompt = identity_context + system_prompt + "\n\n" + memory_context
        
        messages = [
            {'role': 'system', 'content': full_system_prompt}
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
