"""
Example: Integrating Memory Optimizations into Nucleo Agent

This example shows how to integrate all memory optimization components
into the Nucleo agent for maximum efficiency on edge devices.
"""

import asyncio
import logging
from typing import Dict, Optional

# Import memory subsystem
from nucleo.memory import (
    ConversationStore,
    get_lazy_importer,
    get_standard_pools,
    init_gc_for_edge,
    get_memory_monitor,
    get_query_analyzer,
    get_memory_budgets,
    MemoryPressure,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptimizedNucleoAgent:
    """
    Example Nucleo agent with full memory optimizations integrated.
    
    This demonstrates best practices for using the memory subsystem
    on Raspberry Pi and edge devices.
    """

    def __init__(self, memory_limit_mb: int = 100, device_profile: str = "rpi_zero"):
        """
        Initialize optimized agent.
        
        Args:
            memory_limit_mb: Total memory budget in MB
            device_profile: "rpi_zero", "rpi_3", "rpi_4"
        """
        self.memory_limit_mb = memory_limit_mb
        self.device_profile = device_profile
        
        # Memory subsystem components
        self.store: Optional[ConversationStore] = None
        self.lazy = None
        self.pools = None
        self.gc = None
        self.monitor = None
        self.analyzer = None
        self.budgets = None

    async def initialize(self) -> None:
        """Initialize all memory optimizations."""
        logger.info(f"Initializing memory optimizations for {self.device_profile}")

        # 1. Lazy loader (defer expensive imports)
        logger.info("Setting up lazy module loading...")
        self.lazy = get_lazy_importer()
        stats = self.lazy.get_stats()
        logger.info(f"  Lazy loaders ready: {stats['potential_memory_savings_mb']}")

        # 2. Object pooling (reuse common objects)
        logger.info("Setting up object pooling...")
        self.pools = get_standard_pools()

        # 3. Garbage collection (edge-optimized)
        logger.info("Setting up garbage collection...")
        self.gc = init_gc_for_edge()

        # 4. Conversation storage (memory-mapped with compression)
        logger.info("Setting up conversation storage...")
        if self.device_profile == "rpi_zero":
            self.store = ConversationStore(
                max_memory_messages=5,      # Very small in-memory buffer
                compression_level=9,        # Maximum compression
                cleanup_interval=600,       # Clean up every 10 minutes
                archive_threshold=50,       # Archive aggressively
            )
        elif self.device_profile == "rpi_3":
            self.store = ConversationStore(
                max_memory_messages=10,
                compression_level=9,
                cleanup_interval=3600,
                archive_threshold=100,
            )
        else:  # rpi_4 or server
            self.store = ConversationStore(
                max_memory_messages=20,
                compression_level=6,
                cleanup_interval=7200,
                archive_threshold=200,
            )

        # 5. Memory monitoring (real-time tracking)
        logger.info("Setting up memory monitoring...")
        self.monitor = get_memory_monitor(memory_limit_mb=self.memory_limit_mb)
        status = self.monitor.get_status()
        logger.info(f"  Memory status: {status.process_memory_mb:.1f}MB "
                   f"(pressure: {status.pressure.value})")

        # 6. Query complexity analysis (intelligent routing)
        logger.info("Setting up query analyzer...")
        self.analyzer = get_query_analyzer()

        # 7. Memory budgeting (allocation enforcement)
        logger.info("Setting up memory budgets...")
        self.budgets = get_memory_budgets(total_mb=self.memory_limit_mb)

        # Allocate budgets based on device profile
        if self.device_profile == "rpi_zero":
            self.budgets.allocate("agent", 60)
            self.budgets.allocate("tools", 30)
            self.budgets.allocate("cache", 10)
        elif self.device_profile == "rpi_3":
            self.budgets.allocate("agent", 120)
            self.budgets.allocate("tools", 60)
            self.budgets.allocate("cache", 20)
        else:
            self.budgets.allocate("agent", 300)
            self.budgets.allocate("tools", 200)
            self.budgets.allocate("cache", 100)

        # Register cleanup callbacks
        self.budgets.register_cleanup_callback(
            "agent", 
            self._cleanup_agent_memory
        )

        logger.info("Memory optimization initialization complete!")
        logger.info(f"\n{self.budgets.get_summary()}")

    async def handle_query(
        self,
        session_id: str,
        user_query: str,
    ) -> str:
        """
        Handle a user query with memory optimizations.
        
        Args:
            session_id: Conversation session identifier
            user_query: User's query
            
        Returns:
            Assistant response
        """
        # 1. Analyze query complexity for routing
        complexity = self.analyzer.analyze(user_query)
        logger.debug(
            f"Query complexity: {complexity.level.value} "
            f"(suggested model: {complexity.suggested_model})"
        )

        # Check memory pressure
        status = self.monitor.get_status()
        if status.pressure == MemoryPressure.CRITICAL:
            logger.warning("CRITICAL memory pressure - triggering cleanup")
            await self._emergency_cleanup()

        # 2. Add user message to conversation store
        await self.store.add_message(session_id, {
            "role": "user",
            "content": user_query,
        })

        # 3. Request memory budget for processing
        if not self.budgets.request_memory("agent", 5):  # 5MB for processing
            logger.warning("Agent budget exceeded, triggering cleanup")
            await self._cleanup_agent_memory()

        try:
            # 4. Get conversation context
            context = await self.store.get_conversation_context(
                session_id,
                context_size=5 if complexity.level.name == "SIMPLE" else 10,
            )

            logger.debug(
                f"Retrieved {len(context)} context messages "
                f"({complexity.estimated_context_size_tokens} tokens)"
            )

            # 5. Process based on complexity
            if complexity.level.name == "SIMPLE":
                # Use fast path for simple queries
                response = await self._process_simple(user_query, context)
            else:
                # Use full processing for complex queries
                response = await self._process_complex(user_query, context)

        finally:
            # Always release budget
            self.budgets.release_memory("agent", 5)

            # Optional: Manual garbage collection after large operation
            if complexity.estimated_processing_ms > 1000:
                self.gc.collect()

        # 6. Add assistant response to store
        await self.store.add_message(session_id, {
            "role": "assistant",
            "content": response,
        })

        return response

    async def _process_simple(self, query: str, context: list) -> str:
        """Process simple query with minimal overhead."""
        logger.debug("Using fast processing path")
        
        # Use object pool for response
        response_list = self.pools.get_response_list()
        try:
            # Simulate processing
            response_list.append(f"Quick response to: {query}")
            return "\n".join(response_list)
        finally:
            self.pools.return_response_list(response_list)

    async def _process_complex(self, query: str, context: list) -> str:
        """Process complex query with full capability."""
        logger.debug("Using full processing path")
        
        # Use object pool for response
        response_list = self.pools.get_response_list()
        try:
            # Simulate complex processing
            response_list.append(f"Detailed response considering {len(context)} context items:")
            response_list.append("1. ...")
            response_list.append("2. ...")
            return "\n".join(response_list)
        finally:
            self.pools.return_response_list(response_list)

    async def _cleanup_agent_memory(self) -> None:
        """Cleanup strategy when agent budget is low."""
        logger.info("Cleaning up agent memory...")
        
        # Strategy 1: Delete old sessions
        deleted_msgs = await self.store.cleanup_old_conversations(max_age_seconds=3600)
        logger.info(f"  Deleted {deleted_msgs} old messages")
        
        # Strategy 2: Force garbage collection
        self.gc.collect()
        logger.info("  Performed full garbage collection")
        
        # Strategy 3: Clear query analysis cache
        self.analyzer.clear_cache()
        logger.info("  Cleared query cache")

    async def _emergency_cleanup(self) -> None:
        """Emergency cleanup when memory is critical."""
        logger.critical("EMERGENCY MEMORY CLEANUP")
        
        # Delete ALL sessions (nuclear option)
        # In production, might want to save to disk first
        logger.critical("  Clearing all sessions")
        
        # Aggressive GC
        self.gc.collect(2)  # Collect all generations
        logger.critical("  Full GC performed")

    async def get_status(self) -> Dict:
        """Get comprehensive agent status."""
        return {
            "memory": self.monitor.get_status(),
            "budgets": self.budgets.get_all_budgets(),
            "conversation_stats": await self.store.get_statistics(),
            "gc_stats": self.gc.get_stats(),
            "pool_stats": self.pools.manager.get_all_stats(),
        }

    async def shutdown(self) -> None:
        """Gracefully shutdown agent."""
        logger.info("Shutting down optimized agent...")
        
        if self.store:
            await self.store.close()
        
        if self.monitor:
            self.monitor.disable()
        
        if self.gc:
            self.gc.collect()
        
        logger.info("Shutdown complete")


async def demo():
    """Demonstrate the optimized agent."""
    print("\n" + "=" * 80)
    print("NUCLEO MEMORY-OPTIMIZED AGENT DEMO")
    print("=" * 80)

    # Create agent for RPi Zero
    agent = OptimizedNucleoAgent(memory_limit_mb=100, device_profile="rpi_zero")
    await agent.initialize()

    print("\n" + "-" * 80)
    print("Example Conversation")
    print("-" * 80)

    # Simulate conversation
    session_id = "demo_session_001"
    queries = [
        "What is machine learning?",
        "Explain neural networks",
        "How do I train a model?",
        "What about data preprocessing?",
        "Tell me about activation functions",
    ]

    for query in queries:
        print(f"\nUser: {query}")
        response = await agent.handle_query(session_id, query)
        print(f"Assistant: {response}")

    # Show final status
    print("\n" + "-" * 80)
    print("Final Status")
    print("-" * 80)
    status = await agent.get_status()
    print(f"Memory: {status['memory'].process_memory_mb:.1f}MB "
          f"({status['memory'].percent_of_limit:.0f}%)")
    print(f"Pressure: {status['memory'].pressure.value}")
    print(f"Conversation stats: {status['conversation_stats'].total_messages} messages")

    await agent.shutdown()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(demo())
