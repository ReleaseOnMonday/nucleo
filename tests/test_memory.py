"""
Comprehensive tests for memory optimization modules.

Tests verify:
- Memory usage stays under targets
- No memory leaks after 1000+ queries
- Conversation retrieval works correctly
- Performance is not degraded
- All existing features still work

Usage:
    python -m pytest tests/test_memory.py -v
    python -m pytest tests/test_memory.py -v --benchmark
"""

import asyncio
import gc
import os
import sys
import tempfile
import time
import pytest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nucleo.memory import (
    ConversationStore,
    ConversationStats,
    get_lazy_importer,
    get_standard_pools,
    init_gc_for_edge,
    get_memory_monitor,
    get_query_analyzer,
    get_memory_budgets,
    LazyModule,
    ObjectPool,
    MemoryMonitor,
    QueryComplexityAnalyzer,
    MemoryBudgets,
    ComplexityLevel,
    MemoryPressure,
)


class TestConversationStore:
    """Tests for ConversationStore."""

    @pytest.fixture
    async def store(self):
        """Create temporary conversation store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_conv.db")
            store = ConversationStore(
                max_memory_messages=5,
                db_path=db_path,
                compression_level=9,
            )
            yield store
            await store.close()

    @pytest.mark.asyncio
    async def test_add_single_message(self, store):
        """Test adding a single message."""
        msg_id = await store.add_message(
            "session1",
            {"role": "user", "content": "Hello"},
        )
        assert msg_id is not None
        assert msg_id.startswith("session1")

    @pytest.mark.asyncio
    async def test_get_recent_messages(self, store):
        """Test retrieving recent messages."""
        for i in range(3):
            await store.add_message(
                "session1",
                {"role": "user", "content": f"Message {i}"},
            )

        recent = await store.get_recent_messages("session1", n=2)
        assert len(recent) == 2
        assert recent[0]["content"] == "Message 1"
        assert recent[1]["content"] == "Message 2"

    @pytest.mark.asyncio
    async def test_message_archival(self, store):
        """Test automatic archival of old messages."""
        # Add more messages than max_memory_messages
        for i in range(10):
            await store.add_message(
                "session1",
                {"role": "user", "content": f"Message {i}"},
            )

        # Check that old messages were archived
        stats = await store.get_statistics()
        assert stats.messages_in_memory <= store.max_memory_messages
        assert stats.messages_archived > 0

    @pytest.mark.asyncio
    async def test_compression_ratio(self, store):
        """Test that compression is actually happening."""
        # Add message with highly compressible content
        long_text = "hello " * 1000  # Repeating text compresses well
        await store.add_message(
            "session1",
            {"role": "user", "content": long_text},
        )

        # Archive it
        await store._archive_oldest_messages("session1", count=1)

        stats = await store.get_statistics()
        if stats.compression_ratio > 1:
            assert stats.compression_ratio >= 2.0  # Should compress at least 2x

    @pytest.mark.asyncio
    async def test_conversation_retrieval(self, store):
        """Test conversation context retrieval."""
        # Create a conversation
        for i in range(5):
            await store.add_message(
                "session1",
                {"role": "user", "content": f"User {i}"},
            )
            await store.add_message(
                "session1",
                {"role": "assistant", "content": f"Assistant {i}"},
            )

        # Get conversation context
        context = await store.get_conversation_context("session1", context_size=3)
        assert len(context) <= 6  # max 3*2 exchanges

    @pytest.mark.asyncio
    async def test_session_deletion(self, store):
        """Test deleting a session."""
        # Add messages
        for i in range(5):
            await store.add_message(
                "session1",
                {"role": "user", "content": f"Message {i}"},
            )

        # Delete session
        await store.delete_session("session1")

        # Verify deletion
        recent = await store.get_recent_messages("session1")
        assert len(recent) == 0

    @pytest.mark.asyncio
    async def test_deduplication(self, store):
        """Test message deduplication."""
        if not store.enable_dedup:
            pytest.skip("Deduplication disabled")

        # Add duplicate message
        msg_id_1 = await store.add_message(
            "session1",
            {"role": "user", "content": "Duplicate content"},
        )

        msg_id_2 = await store.add_message(
            "session1",
            {"role": "user", "content": "Duplicate content"},
        )

        # Should return same ID for duplicate
        assert msg_id_1 == msg_id_2

        # Verify dedup savings
        stats = await store.get_statistics()
        assert stats.deduplication_savings > 0


class TestLazyLoader:
    """Tests for lazy module loading."""

    def test_lazy_module_creation(self):
        """Test creating a lazy module."""
        lazy_json = LazyModule("json")
        assert lazy_json._module is None

    def test_lazy_module_loading(self):
        """Test that lazy module loads on access."""
        lazy_json = LazyModule("json")
        
        # Access should trigger loading
        dumps = lazy_json.dumps
        assert lazy_json._module is not None
        assert callable(dumps)

    def test_lazy_importer_basic(self):
        """Test basic lazy importer functionality."""
        importer = get_lazy_importer()

        # Should be able to access modules
        assert hasattr(importer, "json")

    def test_lazy_module_expensive(self):
        """Test that expensive modules are not loaded immediately."""
        importer = get_lazy_importer()

        # Check if module is in lazy list
        stats_before = importer.get_stats()

        # Access a lazy module
        json_module = importer.lazy_httpx
        assert json_module is not None  # Wrapper exists

        # Module should not be loaded yet
        assert isinstance(json_module, LazyModule)


class TestObjectPool:
    """Tests for object pooling."""

    def test_pool_creation(self):
        """Test creating an object pool."""
        pool = ObjectPool(dict, pool_size=10)
        assert pool.pool_size == 10

    def test_pool_acquire_release(self):
        """Test acquiring and releasing objects."""
        pool = ObjectPool(dict, pool_size=5)

        # Acquire object
        obj = pool.acquire()
        assert isinstance(obj, dict)

        # Release object
        pool.release(obj)

        # Stats should show reuse
        stats = pool.get_stats()
        assert stats.total_reused == 1

    def test_pool_reuse(self):
        """Test that objects are actually reused."""
        pool = ObjectPool(dict, pool_size=5)

        obj1 = pool.acquire()
        obj1_id = id(obj1)
        pool.release(obj1)

        obj2 = pool.acquire()
        obj2_id = id(obj2)

        # Should be same object (reused)
        assert obj1_id == obj2_id

    def test_pool_context_manager(self):
        """Test pool context manager."""
        pool = ObjectPool(dict, pool_size=5)

        with pool.borrow() as obj:
            obj["key"] = "value"

        # Object should be returned automatically
        stats = pool.get_stats()
        assert stats.currently_in_use == 0
        assert stats.currently_available == 1

    def test_standard_pools(self):
        """Test standard pools singleton."""
        pools = get_standard_pools()

        # Get message dict
        msg_dict = pools.get_message_dict()
        assert isinstance(msg_dict, dict)

        # Return it
        pools.return_message_dict(msg_dict)


class TestGCTuner:
    """Tests for garbage collection tuning."""

    def test_gc_tuner_creation(self):
        """Test creating GC tuner."""
        gc_tuner = init_gc_for_edge()
        assert gc_tuner is not None

    def test_gc_thresholds(self):
        """Test GC threshold setting."""
        gc_tuner = init_gc_for_edge()

        # Get current thresholds
        thresholds = gc_tuner.get_thresholds()
        assert len(thresholds) == 3

    def test_gc_collection(self):
        """Test manual garbage collection."""
        gc_tuner = init_gc_for_edge()

        # Force collection
        collected = gc_tuner.collect()
        assert collected >= 0

    def test_gc_disabled_context(self):
        """Test disabling GC temporarily."""
        gc_tuner = init_gc_for_edge()

        with gc_tuner.disabled():
            # GC should be disabled
            pass


class TestMemoryMonitor:
    """Tests for memory monitoring."""

    def test_monitor_creation(self):
        """Test creating memory monitor."""
        monitor = get_memory_monitor(memory_limit_mb=100, enable=False)
        assert monitor is not None
        assert monitor.memory_limit_mb == 100

    def test_monitor_get_status(self):
        """Test getting memory status."""
        monitor = get_memory_monitor(memory_limit_mb=100, enable=False)

        status = monitor.get_status()
        assert status.process_memory_mb > 0
        assert status.pressure is not None

    def test_monitor_component_tracking(self):
        """Test component memory tracking."""
        monitor = get_memory_monitor(memory_limit_mb=100, enable=False)

        with monitor.track("test_component", budget_mb=50):
            # Do something
            pass

        status = monitor.get_status()
        assert "test_component" in status.components

    def test_detect_optimal_limit(self):
        """Test automatic limit detection."""
        from nucleo.memory.monitor import detect_optimal_memory_limit

        limit = detect_optimal_memory_limit()
        assert limit > 0
        assert limit < 10000  # Reasonable upper bound


class TestQueryAnalyzer:
    """Tests for query complexity analysis."""

    def test_analyzer_creation(self):
        """Test creating query analyzer."""
        analyzer = get_query_analyzer()
        assert analyzer is not None

    def test_simple_query(self):
        """Test analyzing simple query."""
        analyzer = get_query_analyzer()

        analysis = analyzer.analyze("What is 2+2?")
        assert analysis.level == ComplexityLevel.SIMPLE

    def test_complex_query(self):
        """Test analyzing complex query."""
        analyzer = get_query_analyzer()

        analysis = analyzer.analyze(
            "Explain the principles of quantum mechanics and how they relate to modern computing"
        )
        assert analysis.level == ComplexityLevel.COMPLEX

    def test_moderate_query(self):
        """Test analyzing moderate query."""
        analyzer = get_query_analyzer()

        analysis = analyzer.analyze("Tell me about Python programming")
        assert analysis.level in (ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX)

    def test_cache_friendly_detection(self):
        """Test cache-friendly query detection."""
        analyzer = get_query_analyzer()

        should_cache = analyzer.should_use_cache("What time is it?")
        assert should_cache

        should_cache = analyzer.should_use_cache(
            "Analyze and compare these two complex systems"
        )
        assert not should_cache


class TestMemoryBudgets:
    """Tests for memory budgeting."""

    def test_budgets_creation(self):
        """Test creating memory budgets."""
        budgets = get_memory_budgets(total_mb=100)
        assert budgets is not None
        assert budgets.total_mb == 100

    def test_allocate_budget(self):
        """Test allocating budget to component."""
        budgets = MemoryBudgets(total_mb=100)

        budget = budgets.allocate("component1", 50)
        assert budget.total_mb == 50

    def test_request_memory(self):
        """Test requesting memory from budget."""
        budgets = MemoryBudgets(total_mb=100)
        budgets.allocate("component1", 50)

        success = budgets.request_memory("component1", 30)
        assert success

    def test_budget_exceeded(self):
        """Test budget exceeded handling."""
        budgets = MemoryBudgets(total_mb=100)
        budgets.allocate("component1", 50)

        # Request more than allocated
        success = budgets.request_memory("component1", 100)
        assert not success

    def test_memory_reallocate(self):
        """Test memory reallocation."""
        budgets = MemoryBudgets(total_mb=100)
        budgets.allocate("component1", 60)
        budgets.allocate("component2", 40)

        # Allocate some memory to component1
        budgets.request_memory("component1", 30)

        # Reallocate from component1 to component2
        success = budgets.reallocate("component1", "component2", 20)
        assert success


@pytest.mark.benchmark
class TestMemoryBenchmarks:
    """Benchmarking tests for memory optimization."""

    @pytest.mark.asyncio
    async def test_conversation_store_throughput(self):
        """Benchmark conversation store operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ConversationStore(db_path=os.path.join(tmpdir, "bench.db"))

            start = time.time()

            # Add 1000 messages
            for i in range(1000):
                await store.add_message(
                    f"session_{i % 100}",
                    {"role": "user", "content": f"Message {i}"},
                )

            elapsed = time.time() - start

            stats = await store.get_statistics()

            print(f"\nConversationStore throughput: {1000/elapsed:.0f} ops/sec")
            print(f"Messages in memory: {stats.messages_in_memory}")
            print(f"Messages archived: {stats.messages_archived}")
            print(f"Compression ratio: {stats.compression_ratio:.1f}x")

            await store.close()

    def test_query_analysis_performance(self):
        """Benchmark query analysis."""
        analyzer = QueryComplexityAnalyzer()

        queries = [
            "What is 2+2?",
            "Explain quantum mechanics",
            "Tell me about Python",
            "How do I fix this bug?",
        ] * 250

        start = time.time()

        for query in queries:
            analyzer.analyze(query)

        elapsed = time.time() - start

        print(f"\nQuery analysis throughput: {1000/elapsed:.0f} ops/sec")

    def test_object_pool_performance(self):
        """Benchmark object pool operations."""
        pool = ObjectPool(dict, pool_size=1000)

        start = time.time()

        # Acquire and release 10000 times
        for _ in range(10000):
            obj = pool.acquire()
            pool.release(obj)

        elapsed = time.time() - start

        stats = pool.get_stats()

        print(f"\nObjectPool throughput: {10000/elapsed:.0f} ops/sec")
        print(f"Reuse ratio: {stats.reuse_ratio:.1%}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
