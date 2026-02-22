"""Basic tests for Nucleo."""

import pytest
from pathlib import Path
import json

from nucleo import Config, Agent
from nucleo.tools import BashTool, FilesTool


def test_config_load(tmp_path):
    """Test configuration loading."""
    config_file = tmp_path / "test_config.json"
    config_data = {
        "agent": {
            "model": "claude-3-5-sonnet-20241022"
        }
    }
    
    config_file.write_text(json.dumps(config_data))
    
    config = Config().load(str(config_file))
    assert config.get('agent.model') == 'claude-3-5-sonnet-20241022'


def test_config_dot_notation():
    """Test dot notation access."""
    config = Config()
    config.set('agent.model', 'test-model')
    config.set('tools.bash.enabled', True)
    
    assert config.get('agent.model') == 'test-model'
    assert config.get('tools.bash.enabled') is True
    assert config.get('nonexistent.key', 'default') == 'default'


def test_bash_tool_allowed_commands():
    """Test bash tool command filtering."""
    tool = BashTool({'allowed_commands': ['ls', 'echo']})
    
    assert tool._is_allowed('ls -la')
    assert tool._is_allowed('echo hello')
    assert not tool._is_allowed('rm -rf /')


@pytest.mark.asyncio
async def test_bash_tool_execution():
    """Test bash command execution."""
    tool = BashTool({'allowed_commands': ['echo']})
    
    result = await tool.execute(command='echo "hello"')
    
    assert result['success'] is True
    assert 'hello' in result['stdout']


@pytest.mark.asyncio
async def test_files_tool_read_write(tmp_path):
    """Test file operations."""
    tool = FilesTool({'workspace': str(tmp_path)})
    
    # Write file
    write_result = await tool.execute(
        operation='write',
        path='test.txt',
        content='Hello World'
    )
    assert write_result['success'] is True
    
    # Read file
    read_result = await tool.execute(
        operation='read',
        path='test.txt'
    )
    assert read_result['success'] is True
    assert read_result['content'] == 'Hello World'


@pytest.mark.asyncio
async def test_files_tool_sandbox(tmp_path):
    """Test that files tool is sandboxed."""
    tool = FilesTool({'workspace': str(tmp_path)})
    
    # Try to escape workspace
    result = await tool.execute(
        operation='read',
        path='../../etc/passwd'
    )
    
    assert result['success'] is False
    assert 'Invalid path' in result['error']


def test_tool_to_anthropic_format():
    """Test tool conversion to Anthropic format."""
    tool = BashTool({})
    anthropic_tool = tool.to_anthropic_tool()
    
    assert anthropic_tool['name'] == 'bash'
    assert 'description' in anthropic_tool
    assert 'input_schema' in anthropic_tool


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
