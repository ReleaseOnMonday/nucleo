"""
QUICK START: Memory Optimizations for Nucleo

This guide shows how to integrate memory optimizations into the existing
Nucleo codebase with minimal changes.
"""

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# STEP 1: Update main.py or your agent startup
# ============================================================================

STEP_1_STARTUP_CODE = '''
# In your main.py or agent initialization:

import asyncio
from nucleo.agent import Agent
from nucleo.memory import (
    ConversationStore,
    get_lazy_importer,
    get_standard_pools,
    init_gc_for_edge,
    get_memory_monitor,
    get_query_analyzer,
    get_memory_budgets,
)

async def setup_agent():
    """Initialize agent with memory optimizations."""
    
    # Initialize memory subsystem early
    logger.info("Setting up memory optimizations...")
    
    # 1. Setup GC tuning (2 lines)
    gc_tuner = init_gc_for_edge()
    
    # 2. Setup conversation store (3 lines)
    store = ConversationStore(
        max_memory_messages=10,
        compression_level=9,
    )
    
    # 3. Setup memory monitoring (1 line)
    monitor = get_memory_monitor(memory_limit_mb=100)
    
    # 4. Setup lazy loader (automatically applied on imports after this point)
    lazy = get_lazy_importer()
    
    # 5. Setup query analyzer (1 line)
    analyzer = get_query_analyzer()
    
    # 6. Setup memory budgets (4 lines)
    budgets = get_memory_budgets(total_mb=100)
    budgets.allocate("agent", 60)
    budgets.allocate("tools", 30)
    budgets.allocate("cache", 10)
    
    # Now create your agent
    agent = Agent()
    
    # Attach memory subsystem to agent for use in methods
    agent.memory_store = store
    agent.memory_monitor = monitor
    agent.memory_budgets = budgets
    agent.query_analyzer = analyzer
    
    return agent

# In main:
if __name__ == "__main__":
    agent = asyncio.run(setup_agent())
    agent.run()
'''

# ============================================================================
# STEP 2: Update agent.py to use conversation store
# ============================================================================

STEP_2_AGENT_CODE = '''
# In nucleo/agent.py:

class Agent:
    async def chat(self, session_id: str, user_message: str) -> str:
        """Process a user message."""
        
        # 1. Add user message to store (2 lines)
        await self.memory_store.add_message(session_id, {
            "role": "user",
            "content": user_message,
        })
        
        # 2. Get conversation context instead of full history (1 line)
        context = await self.memory_store.get_conversation_context(
            session_id, context_size=5
        )
        
        # 3. Check memory budget before processing (3 lines)
        if not self.memory_budgets.request_memory("agent", 5):
            logger.warning("Memory budget exceeded, running cleanup")
            await self.memory_store.cleanup_old_conversations()
        
        try:
            # 4. Analyze query complexity to route appropriately (2 lines)
            complexity = self.query_analyzer.analyze(user_message)
            logger.debug(f"Query complexity: {complexity.level.value}")
            
            # 5. Process query using existing methods
            response = await self._process_query(user_message, context)
            
        finally:
            # 6. Release memory budget (1 line)
            self.memory_budgets.release_memory("agent", 5)
        
        # 7. Add response to store (2 lines)
        await self.memory_store.add_message(session_id, {
            "role": "assistant",
            "content": response,
        })
        
        # 8. Check memory pressure (optional but recommended) (2 lines)
        status = self.memory_monitor.get_status()
        if status.pressure.value == "critical":
            await self._emergency_cleanup()
        
        return response
'''

# ============================================================================
# STEP 3: Update tools to use object pooling
# ============================================================================

STEP_3_TOOLS_CODE = '''
# In nucleo/tools/base.py:

from nucleo.memory import get_standard_pools

class Tool:
    async def execute(self, *args, **kwargs):
        """Execute tool with memory optimization."""
        
        # Use object pool for response building
        pools = get_standard_pools()
        response_list = pools.get_response_list()
        
        try:
            # Build response
            response_list.append("Tool output...")
            result = "\\n".join(response_list)
        finally:
            # Always return to pool
            pools.return_response_list(response_list)
        
        return result
'''

# ============================================================================
# STEP 4: Add memory monitoring to CLI
# ============================================================================

STEP_4_CLI_CODE = '''
# Add to CLI commands:

@cli.command()
async def memory_status():
    """Show current memory status."""
    from nucleo.memory import get_memory_monitor
    
    monitor = get_memory_monitor(enable=False)
    status = monitor.get_status()
    
    print(monitor.get_memory_report())

@cli.command()
async def memory_benchmark():
    """Run memory benchmarks."""
    from benchmarks.memory_benchmark import benchmark_full_suite, BenchmarkResults
    
    results = BenchmarkResults()
    await benchmark_full_suite(results, quick=False)
    results.print_results()
'''

# ============================================================================
# STEP 5: Configuration for different devices
# ============================================================================

CONFIG_EXAMPLE = '''
# In config.json, add memory section:

{
    "memory": {
        "device_profile": "rpi_zero",  # or "rpi_3", "rpi_4", "server"
        "conversation_store": {
            "max_memory_messages": 10,
            "compression_level": 9,
            "cleanup_interval": 3600,
            "archive_threshold": 100
        },
        "memory_monitor": {
            "enabled": true,
            "memory_limit_mb": 100,
            "alert_on_pressure": true
        },
        "budgets": {
            "total_mb": 100,
            "agent": 60,
            "tools": 30,
            "cache": 10
        }
    }
}
'''

# ============================================================================
# STEP 6: Testing
# ============================================================================

TEST_EXAMPLE = '''
# Run tests to verify integration:

# Run all memory tests
pytest tests/test_memory.py -v

# Run specific component tests
pytest tests/test_memory.py::TestConversationStore -v
pytest tests/test_memory.py::TestMemoryMonitor -v

# Run benchmarks
python benchmarks/memory_benchmark.py --quick
'''

# ============================================================================
# CHECKLIST
# ============================================================================

INTEGRATION_CHECKLIST = '''
INTEGRATION CHECKLIST
=====================

Phase 1: Core Setup (15 minutes)
  [ ] Add memory initialization to main startup code
  [ ] Add ConversationStore initialization
  [ ] Add MemoryMonitor initialization
  [ ] Verify startup memory < 20MB (was ~50MB)
  
Phase 2: Agent Integration (30 minutes)
  [ ] Update Agent.chat() to use conversation store
  [ ] Add context retrieval from store
  [ ] Add memory budget checking
  [ ] Update existing code to get context from store
  [ ] Test conversation functionality
  
Phase 3: Tool Updates (20 minutes)
  [ ] Update tools to use object pooling
  [ ] Replace list/dict creation with pool requests
  [ ] Add proper cleanup/return to pools
  [ ] Test tool execution
  
Phase 4: Monitoring & Budgets (15 minutes)
  [ ] Add memory pressure checking in main loop
  [ ] Add emergency cleanup trigger
  [ ] Configure memory budgets
  [ ] Add monitoring to CLI if applicable
  
Phase 5: Testing & Tuning (30 minutes)
  [ ] Run test suite
  [ ] Run benchmarks
  [ ] Profile your specific use case
  [ ] Tune parameters for your device
  [ ] Verify no memory leaks over 1000+ queries
  
Total Time: ~2 hours for complete integration

VERIFICATION
============
After integration, verify:
1. Startup memory: pytest for baseline < 20MB
2. Query processing: Single query < 30MB peak
3. Long running: <1MB leak per 1000 queries
4. Device compatibility: Works on target RPi model
'''

# ============================================================================
# DEVICE-SPECIFIC CONFIGURATIONS
# ============================================================================

DEVICE_PROFILES = {
    "rpi_zero": {
        "description": "Raspberry Pi Zero (512MB RAM)",
        "memory_limit": 100,
        "max_memory_messages": 5,
        "compression_level": 9,
        "cleanup_interval": 600,
        "budgets": {
            "agent": 60,
            "tools": 30,
            "cache": 10,
        },
    },
    "rpi_3": {
        "description": "Raspberry Pi 3 (1GB RAM)",
        "memory_limit": 200,
        "max_memory_messages": 10,
        "compression_level": 9,
        "cleanup_interval": 3600,
        "budgets": {
            "agent": 120,
            "tools": 60,
            "cache": 20,
        },
    },
    "rpi_4": {
        "description": "Raspberry Pi 4 (2-8GB RAM)",
        "memory_limit": 400,
        "max_memory_messages": 20,
        "compression_level": 6,
        "cleanup_interval": 7200,
        "budgets": {
            "agent": 300,
            "tools": 200,
            "cache": 100,
        },
    },
    "server": {
        "description": "Server (16GB+ RAM)",
        "memory_limit": 2000,
        "max_memory_messages": 50,
        "compression_level": 4,
        "cleanup_interval": 14400,
        "budgets": {
            "agent": 1000,
            "tools": 500,
            "cache": 500,
        },
    },
}

# ============================================================================
# COMMON INTEGRATION PATTERNS
# ============================================================================

PATTERN_1_MINIMAL = '''
# Minimal integration (just store + monitor):

from nucleo.memory import ConversationStore, get_memory_monitor, init_gc_for_edge

# One-time setup
store = ConversationStore(max_memory_messages=10)
monitor = get_memory_monitor(memory_limit_mb=100)
init_gc_for_edge()

# In your query handler
await store.add_message(session_id, {"role": "user", "content": message})
context = await store.get_conversation_context(session_id, context_size=5)
response = process(context)
await store.add_message(session_id, {"role": "assistant", "content": response})
'''

PATTERN_2_FULL = '''
# Full integration (all optimizations):

from nucleo.memory import (
    ConversationStore,
    get_lazy_importer,
    get_standard_pools,
    init_gc_for_edge,
    get_memory_monitor,
    get_query_analyzer,
    get_memory_budgets,
)

# Setup
store = ConversationStore(max_memory_messages=10)
pools = get_standard_pools()
gc = init_gc_for_edge()
monitor = get_memory_monitor(memory_limit_mb=100)
analyzer = get_query_analyzer()
budgets = get_memory_budgets(total_mb=100)
budgets.allocate("agent", 60)
budgets.allocate("tools", 30)

# In handler
complexity = analyzer.analyze(message)
if not budgets.request_memory("agent", 5):
    await cleanup()

try:
    await store.add_message(session_id, {"role": "user", "content": message})
    context = await store.get_conversation_context(session_id)
    response = process(context)
    await store.add_message(session_id, {"role": "assistant", "content": response})
finally:
    budgets.release_memory("agent", 5)
    gc.collect()
'''

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

TROUBLESHOOTING = '''
TROUBLESHOOTING INTEGRATION
============================

Q: "ImportError: No module named nucleo.memory"
A: Make sure nucleo/memory/__init__.py exists with proper imports

Q: "Memory still growing over time"
A: Enable cleanup: store.cleanup_interval = 600 (cleanup every 10 min)
   Or call manually: await store.cleanup_old_conversations()

Q: "Getting 'Budget exceeded' errors"
A: Increase budget sizes: budgets.allocate("agent", 100)  # was 60
   Or use aggressive cleanup trigger

Q: "Queries are slower than before"
A: Reduce compression level: ConversationStore(compression_level=6)
   Or reduce archive threshold: archive_threshold=50

Q: "Object pool not helping"
A: Verify code is actually using pools:
   - search for get_message_dict() calls
   - Check pool stats: pools.manager.get_all_stats()

Q: "Tests failing with memory issues"
A: Use quick mode: pytest tests/test_memory.py --quick
   Or increase limits in test fixtures

Q: "Lazy loading not working"
A: Verify module is in LAZY_MODULES list
   Check manually: from nucleo.memory.lazy_loader import get_lazy_importer
                   lazy = get_lazy_importer()
                   lazy.ensure_loaded("httpx")
'''

# ============================================================================
# Print all guides
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("NUCLEO MEMORY OPTIMIZATION - QUICK START GUIDE")
    print("=" * 80)

    print("\n" + "-" * 80)
    print("STEP 1: Startup Code")
    print("-" * 80)
    print(STEP_1_STARTUP_CODE)

    print("\n" + "-" * 80)
    print("STEP 2: Agent Integration")
    print("-" * 80)
    print(STEP_2_AGENT_CODE)

    print("\n" + "-" * 80)
    print("STEP 3: Tool Updates")
    print("-" * 80)
    print(STEP_3_TOOLS_CODE)

    print("\n" + "-" * 80)
    print("STEP 4: CLI Monitoring")
    print("-" * 80)
    print(STEP_4_CLI_CODE)

    print("\n" + "-" * 80)
    print("STEP 5: Configuration")
    print("-" * 80)
    print(CONFIG_EXAMPLE)

    print("\n" + "-" * 80)
    print("DEVICE PROFILES")
    print("-" * 80)
    for profile_name, config in DEVICE_PROFILES.items():
        print(f"\n{profile_name}: {config['description']}")
        for key, value in config.items():
            if key != "description":
                print(f"  {key}: {value}")

    print("\n" + "-" * 80)
    print("INTEGRATION CHECKLIST")
    print("-" * 80)
    print(INTEGRATION_CHECKLIST)

    print("\n" + "-" * 80)
    print("INTEGRATION PATTERNS")
    print("-" * 80)
    print("Minimal (store + monitor):")
    print(PATTERN_1_MINIMAL)
    print("\nFull (all optimizations):")
    print(PATTERN_2_FULL)

    print("\n" + "-" * 80)
    print("TROUBLESHOOTING")
    print("-" * 80)
    print(TROUBLESHOOTING)

    print("\n" + "=" * 80)
