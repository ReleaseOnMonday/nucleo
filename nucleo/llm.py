"""Lightweight LLM client with Ollama support (free local models)."""

import json
from typing import AsyncIterator, Dict, List, Optional, Any
import httpx

# Lazy import for memory efficiency
_anthropic_client = None


def get_anthropic_client(api_key: str):
    """Lazy load Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        _anthropic_client = Anthropic(api_key=api_key)
    return _anthropic_client


class LLMClient:
    """Lightweight LLM client with Ollama and Anthropic support."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize LLM client.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.provider = self._detect_provider()
        
    def _detect_provider(self) -> str:
        """Detect which provider to use based on configuration."""
        # Check if Ollama is explicitly enabled
        if self.config.get('providers', {}).get('ollama', {}).get('enabled'):
            return 'ollama'
        
        model = self.config.get('agent', {}).get('model', '')
        
        # Auto-detect based on model name
        if 'claude' in model.lower():
            return 'anthropic'
        elif 'gpt' in model.lower():
            return 'openai'
        elif any(x in model.lower() for x in ['llama', 'mistral', 'phi', 'qwen']):
            return 'ollama'
        else:
            return 'anthropic'  # Default
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream chat completion with optional tools.
        
        Args:
            messages: Chat messages
            tools: Optional tool definitions
            
        Yields:
            Chunks of the response
        """
        if self.provider == 'ollama':
            async for chunk in self._ollama_stream(messages, tools):
                yield chunk
        elif self.provider == 'anthropic':
            async for chunk in self._anthropic_stream(messages, tools):
                yield chunk
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented")
    
    async def _ollama_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream from Ollama (local models).
        
        Args:
            messages: Chat messages
            tools: Optional tool definitions
            
        Yields:
            Response chunks
        """
        ollama_config = self.config.get('providers', {}).get('ollama', {})
        base_url = ollama_config.get('base_url', 'http://localhost:11434')
        model = self.config.get('agent', {}).get('model', 'llama3.2')
        
        # Convert messages format
        ollama_messages = []
        system_message = None
        
        for msg in messages:
            if msg.get('role') == 'system':
                system_message = msg.get('content')
            elif isinstance(msg.get('content'), str):
                # Simple text message
                ollama_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            elif isinstance(msg.get('content'), list):
                # Complex message with tool results
                for item in msg['content']:
                    if item.get('type') == 'text':
                        ollama_messages.append({
                            'role': msg['role'],
                            'content': item['text']
                        })
                    elif item.get('type') == 'tool_result':
                        # Add tool result as user message
                        ollama_messages.append({
                            'role': 'user',
                            'content': f"Tool result: {item.get('content', '')}"
                        })
        
        # Build request
        request_data = {
            'model': model,
            'messages': ollama_messages,
            'stream': True,
        }
        
        if system_message:
            request_data['system'] = system_message
        
        # Note: Ollama's tool support is limited, so we simplify tool calls
        # by including tool descriptions in the system prompt
        if tools:
            tool_descriptions = self._format_tools_for_prompt(tools)
            if system_message:
                request_data['system'] = f"{system_message}\n\n{tool_descriptions}"
            else:
                request_data['system'] = tool_descriptions
        
        # Stream response
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    'POST',
                    f'{base_url}/api/chat',
                    json=request_data
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield {
                            'type': 'error',
                            'content': f'Ollama error ({response.status_code}): {error_text.decode()}\n\nMake sure Ollama is running: ollama serve'
                        }
                        return
                    
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                
                                # Extract content
                                if 'message' in data:
                                    content = data['message'].get('content', '')
                                    if content:
                                        yield {
                                            'type': 'text',
                                            'content': content
                                        }
                                
                            except json.JSONDecodeError:
                                continue
                            
        except httpx.ConnectError:
            yield {
                'type': 'error',
                'content': '❌ Cannot connect to Ollama.\n\nPlease start Ollama:\n  ollama serve\n\nOr install it from: https://ollama.com'
            }
        except Exception as e:
            yield {
                'type': 'error',
                'content': f'Ollama error: {str(e)}'
            }
    
    def _format_tools_for_prompt(self, tools: List[Dict]) -> str:
        """Format tools as text for inclusion in system prompt.
        
        Args:
            tools: Tool definitions
            
        Returns:
            Formatted tool descriptions
        """
        tool_text = "You have access to the following tools:\n\n"
        
        for tool in tools:
            tool_text += f"- {tool['name']}: {tool['description']}\n"
            params = tool.get('input_schema', {}).get('properties', {})
            if params:
                tool_text += "  Parameters:\n"
                for param_name, param_info in params.items():
                    param_desc = param_info.get('description', '')
                    tool_text += f"    - {param_name}: {param_desc}\n"
        
        tool_text += "\nTo use a tool, respond with: USE_TOOL: tool_name(param1=value1, param2=value2)"
        
        return tool_text
    
    async def _anthropic_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream from Anthropic API.
        
        Args:
            messages: Chat messages
            tools: Optional tool definitions
            
        Yields:
            Response chunks
        """
        api_key = self.config.get('providers', {}).get('anthropic', {}).get('api_key')
        if not api_key:
            raise ValueError("Anthropic API key not configured")
        
        client = get_anthropic_client(api_key)
        
        # Extract system message
        system_message = None
        chat_messages = []
        
        for msg in messages:
            if msg.get('role') == 'system':
                system_message = msg.get('content')
            else:
                chat_messages.append(msg)
        
        # Build request parameters
        params = {
            'model': self.config.get('agent', {}).get('model', 'claude-3-5-sonnet-20241022'),
            'max_tokens': self.config.get('agent', {}).get('max_tokens', 4096),
            'temperature': self.config.get('agent', {}).get('temperature', 0.7),
            'messages': chat_messages,
        }
        
        if system_message:
            params['system'] = system_message
        
        if tools:
            params['tools'] = tools
        
        # Stream response
        with client.messages.stream(**params) as stream:
            for text in stream.text_stream:
                yield {
                    'type': 'text',
                    'content': text
                }
            
            # Get final message for tool use
            final_message = stream.get_final_message()
            
            # Check for tool use
            for block in final_message.content:
                if block.type == 'tool_use':
                    yield {
                        'type': 'tool_use',
                        'id': block.id,
                        'name': block.name,
                        'input': block.input
                    }
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Non-streaming chat completion.
        
        Args:
            messages: Chat messages
            tools: Optional tool definitions
            
        Returns:
            Complete response
        """
        response = {
            'content': '',
            'tool_calls': []
        }
        
        async for chunk in self.chat_stream(messages, tools):
            if chunk['type'] == 'text':
                response['content'] += chunk['content']
            elif chunk['type'] == 'tool_use':
                response['tool_calls'].append(chunk)
            elif chunk['type'] == 'error':
                response['content'] += chunk['content']
        
        return response
