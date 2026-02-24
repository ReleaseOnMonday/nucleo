"""Interactive setup wizard for Nucleo configuration."""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List


class SetupWizard:
    """Interactive setup wizard for Nucleo."""
    
    def __init__(self):
        """Initialize setup wizard."""
        self.config: Dict[str, Any] = {
            'llm': {},
            'tools': {},
            'channels': {},
            'memory': {'enabled': True},
            'identity': {'enabled': True},
            'scheduler': {'enabled': False}
        }
        self.config_path = Path.cwd() / 'config.json'
    
    def run(self):
        """Run the complete setup wizard."""
        self.print_header()
        
        # Step 1: Detect environment
        self.detect_environment()
        
        # Step 2: Configure LLM
        self.configure_llm()
        
        # Step 3: Configure channels
        self.configure_channels()
        
        # Step 4: Configure tools
        self.configure_tools()
        
        # Step 5: Review and save
        self.review_and_save()
        
        print("\n✅ Setup complete!")
        print(f"Config saved to: {self.config_path}")
    
    def print_header(self):
        """Print setup wizard header."""
        print("""
╔════════════════════════════════════════════════════════════════╗
║                  🚀 Nucleo Setup Wizard                         ║
║                                                                 ║
║  Welcome to Nucleo! This wizard will help you configure the    ║
║  AI agent for multi-channel communication.                     ║
║                                                                 ║
║  Setup typically takes 2-3 minutes.                            ║
╚════════════════════════════════════════════════════════════════╝
        """)
    
    def detect_environment(self):
        """Detect available LLM providers and tools."""
        print("🔍 Detecting environment...\n")
        
        # Check for Ollama
        ollama_available = self._check_ollama()
        if ollama_available:
            print("✅ Ollama detected (local LLM available)")
        else:
            print("⚠️  Ollama not running (you can run it later)")
        
        # Check for Claude API key
        claude_key = os.getenv('ANTHROPIC_API_KEY')
        if claude_key:
            print("✅ Claude API key detected")
        else:
            print("⚠️  No Claude API key found (needed for cloud LLM)")
        
        # Check for bash
        try:
            subprocess.run(['bash', '--version'], capture_output=True, check=True)
            print("✅ Bash available (can execute shell commands)")
        except:
            print("⚠️  Bash not available")
        
        print()
    
    def configure_llm(self):
        """Configure language model."""
        print("🧠 Configuring Language Model\n")
        
        options = {
            '1': 'Claude 3.5 Sonnet (requires API key)',
            '2': 'Ollama (offline, local)',
            '3': 'Auto-detect (try Ollama, fall back to Claude)',
        }
        
        for key, desc in options.items():
            print(f"  {key}. {desc}")
        
        choice = self.get_input("Choose LLM provider (enter number)", default='3')
        
        if choice == '1':
            print("\n📝 Claude API Setup:")
            print("   Get your API key from: https://console.anthropic.com/")
            api_key = self.get_input("Enter your Claude API key (or press Enter to skip)", default='')
            if api_key:
                os.environ['ANTHROPIC_API_KEY'] = api_key
                self.config['llm']['provider'] = 'anthropic'
                self.config['llm']['model'] = 'claude-3-5-sonnet-20241022'
                print("✅ Claude configured")
            else:
                print("⚠️  Skipped Claude setup")
        
        elif choice == '2':
            print("\n📝 Ollama Setup:")
            print("   Install Ollama from: https://ollama.ai/")
            print("   Start with: ollama serve")
            model = self.get_input("Which Ollama model to use?", default='llama3.2')
            self.config['llm']['provider'] = 'ollama'
            self.config['llm']['model'] = model
            print(f"✅ Ollama configured with {model}")
        
        else:  # Auto-detect
            self.config['llm']['provider'] = 'auto'
            print("✅ Auto-detect mode configured")
        
        print()
    
    def configure_channels(self):
        """Configure communication channels."""
        print("💬 Configuring Channels\n")
        
        channels_config = {
            'telegram': False,
            'discord': False,
        }
        
        print("Which channels would you like to enable?\n")
        
        # Telegram
        if self.get_yes_no("  Configure Telegram?"):
            self.setup_telegram()
            channels_config['telegram'] = True
        
        # Discord
        if self.get_yes_no("  Configure Discord?"):
            self.setup_discord()
            channels_config['discord'] = True
        
        if not any(channels_config.values()):
            print("\n⚠️  No channels configured. You can add them later in config.json")
        
        print()
    
    def setup_telegram(self):
        """Setup Telegram channel."""
        print("\n📱 Telegram Setup:")
        print("   1. Talk to @BotFather on Telegram")
        print("   2. Create a new bot with /newbot command")
        print("   3. Copy the API token")
        print("   4. Add your Telegram user ID to the allowlist")
        print()
        
        token = self.get_input("Telegram Bot Token (or press Enter to skip)", default='')
        if token:
            user_ids = self.get_input("Allowed user IDs (comma-separated, or press Enter for any user)", default='')
            allowed_users = [int(x.strip()) for x in user_ids.split(',') if x.strip()] if user_ids else []
            
            self.config['channels']['telegram'] = {
                'enabled': True,
                'token': token,
                'allowed_users': allowed_users,
                'description': 'Telegram bot channel'
            }
            print("✅ Telegram configured")
        else:
            print("⚠️  Telegram skipped")
    
    def setup_discord(self):
        """Setup Discord channel."""
        print("\n🎮 Discord Setup:")
        print("   1. Go to: https://discord.com/developers/applications")
        print("   2. Create a New Application")
        print("   3. Go to 'Bot' section and click 'Add Bot'")
        print("   4. Copy the 'TOKEN' value")
        print("   5. Enable required intents (Message Content, etc.)")
        print("   6. Go to OAuth2 > URL Generator, select 'bot' scope")
        print("   7. Select permissions (Send Messages, Read Messages, etc.)")
        print("   8. Copy the generated URL and invite bot to your server")
        print()
        
        token = self.get_input("Discord Bot Token (or press Enter to skip)", default='')
        if token:
            guild_ids = self.get_input("Allowed Guild IDs (comma-separated, or press Enter for any guild)", default='')
            allowed_guilds = [int(x.strip()) for x in guild_ids.split(',') if x.strip()] if guild_ids else []
            
            self.config['channels']['discord'] = {
                'enabled': True,
                'token': token,
                'allowed_guilds': allowed_guilds,
                'description': 'Discord bot channel'
            }
            print("✅ Discord configured")
        else:
            print("⚠️  Discord skipped")
    
    def configure_tools(self):
        """Configure tools."""
        print("🔧 Configuring Tools\n")
        
        # Files tool (always available)
        self.config['tools']['files'] = {
            'enabled': True,
            'workspace_path': str(Path.cwd() / 'workspace'),
            'description': 'File operations and management'
        }
        print("✅ Files tool enabled")
        
        # Bash tool
        if self.get_yes_no("  Enable bash execution tool?"):
            self.config['tools']['bash'] = {
                'enabled': True,
                'description': 'Execute bash commands'
            }
            print("✅ Bash tool enabled")
        
        # Search tool
        if self.get_yes_no("  Enable web search tool? (requires BRAVE_SEARCH_API_KEY)"):
            api_key = self.get_input("Brave Search API key (or press Enter to skip)", default='')
            if api_key:
                os.environ['BRAVE_SEARCH_API_KEY'] = api_key
                self.config['tools']['search'] = {
                    'enabled': True,
                    'description': 'Web search capability'
                }
                print("✅ Search tool enabled")
            else:
                print("⚠️  Search tool skipped")
        
        print()
    
    def review_and_save(self):
        """Review configuration and save."""
        print("📋 Configuration Review\n")
        print(json.dumps(self.config, indent=2))
        print()
        
        if self.get_yes_no("Save this configuration?", default=True):
            # Load existing config if it exists
            if self.config_path.exists():
                try:
                    with open(self.config_path) as f:
                        existing = json.load(f)
                    # Merge with existing
                    existing.update(self.config)
                    self.config = existing
                except:
                    pass
            
            # Save config
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            print(f"\n✅ Config saved to {self.config_path}")
            
            # Create blank identity files if they don't exist
            self._create_identity_files()
            
        else:
            print("\n⚠️  Configuration not saved")
    
    def _create_identity_files(self):
        """Create blank identity files if they don't exist."""
        workspace_path = Path.cwd() / 'workspace'
        workspace_path.mkdir(exist_ok=True)
        
        files = {
            'IDENTITY.md': 'identity',
            'SOUL.md': 'soul',
            'USER.md': 'user'
        }
        
        for filename, file_type in files.items():
            filepath = workspace_path / filename
            if not filepath.exists():
                filepath.touch()
                print(f"✅ Created {filename} (edit to customize)")
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            import httpx
            response = httpx.get('http://localhost:11434/api/tags', timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_input(self, prompt: str, default: str = '') -> str:
        """Get user input with optional default."""
        if default:
            prompt = f"{prompt} [{default}]"
        prompt += ": "
        
        response = input(prompt).strip()
        return response if response else default
    
    def get_yes_no(self, prompt: str, default: bool = False) -> bool:
        """Get yes/no response from user."""
        default_str = "Y/n" if default else "y/N"
        prompt = f"{prompt} ({default_str})"
        
        response = input(f"{prompt}: ").strip().lower()
        
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        else:
            return default


def run_setup():
    """Run the setup wizard."""
    wizard = SetupWizard()
    wizard.run()


if __name__ == '__main__':
    run_setup()
