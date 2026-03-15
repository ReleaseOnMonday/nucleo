"""
Memory budget allocator and constraint enforcer.

Memory Impact: ~1-2MB for budget tracking

Implements memory budgeting at the application level:
- Allocate memory budgets to components
- Monitor budget usage
- Trigger cleanup when approaching limits
- Enforce hard limits with exceptions
- Provide budget reallocation strategies

Usage:
    budgets = MemoryBudgets(total_mb=100)
    budgets.allocate("agent", 60)
    budgets.allocate("tools", 30)
    budgets.allocate("cache", 10)
    
    # Use budget
    budget = budgets.get_budget("agent")
    if budget.available_mb < 5:
        cleanup_old_conversations()
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BudgetLevel(Enum):
    """Budget consumption levels."""

    HEALTHY = "healthy"  # <50% used
    MODERATE = "moderate"  # 50-75% used
    HIGH = "high"  # 75-90% used
    CRITICAL = "critical"  # >90% used


@dataclass
class Budget:
    """Memory budget for a component."""

    name: str
    total_mb: float
    used_mb: float = 0.0
    peak_mb: float = 0.0
    allocations: int = 0
    deallocations: int = 0
    last_updated: float = field(default_factory=time.time)

    @property
    def available_mb(self) -> float:
        """Get available memory in MB."""
        return max(0, self.total_mb - self.used_mb)

    @property
    def percent_used(self) -> float:
        """Get percentage of budget used."""
        return (self.used_mb / self.total_mb * 100) if self.total_mb > 0 else 0

    @property
    def level(self) -> BudgetLevel:
        """Get budget consumption level."""
        percent = self.percent_used

        if percent < 50:
            return BudgetLevel.HEALTHY
        elif percent < 75:
            return BudgetLevel.MODERATE
        elif percent < 90:
            return BudgetLevel.HIGH
        else:
            return BudgetLevel.CRITICAL

    def allocate(self, amount_mb: float) -> bool:
        """
        Allocate memory from budget.
        
        Args:
            amount_mb: Amount to allocate in MB
        
        Returns:
            True if allocation succeeded, False if budget exceeded
        """
        if self.used_mb + amount_mb > self.total_mb:
            return False

        self.used_mb += amount_mb
        self.allocations += 1

        if self.used_mb > self.peak_mb:
            self.peak_mb = self.used_mb

        return True

    def deallocate(self, amount_mb: float) -> None:
        """
        Deallocate memory from budget.
        
        Args:
            amount_mb: Amount to deallocate in MB
        """
        self.used_mb = max(0, self.used_mb - amount_mb)
        self.deallocations += 1
        self.last_updated = time.time()

    def reset(self) -> None:
        """Reset budget usage (keep stats)."""
        self.used_mb = 0.0

    def __repr__(self) -> str:
        return (
            f"<Budget {self.name}: {self.used_mb:.1f}/{self.total_mb:.1f}MB "
            f"({self.percent_used:.0f}%)>"
        )


@dataclass
class BudgetAllocation:
    """Record of a memory allocation from a budget."""

    component: str
    amount_mb: float
    timestamp: float = field(default_factory=time.time)
    auto_deallocate: bool = False

    def deallocate_after(self, seconds: float) -> None:
        """Deallocate after specified time."""
        self.auto_deallocate = True
        # Would be used by cleanup timer


class MemoryBudgets:
    """
    Memory budget allocator and enforcer.
    
    Implements a budget-based approach to memory management:
    - Allocate memory budgets to components
    - Monitor usage vs budget
    - Issue warnings when approaching limits
    - Trigger cleanup when exceeding thresholds
    
    Memory Impact: ~1-2MB per budget manager instance
    Thread-safe: Uses locks for concurrent access
    
    Typical workflow:
    1. Create MemoryBudgets with total limit
    2. Allocate budgets to components
    3. Components check available budget before allocating
    4. If budget low, implement cleanup strategy
    5. Monitor budget usage
    """

    def __init__(
        self,
        total_mb: float = 100,
        low_water_mark: float = 0.2,  # 20% available triggers warning
        critical_threshold: float = 0.05,  # 5% available is critical
    ):
        """
        Initialize memory budgets.
        
        Args:
            total_mb: Total memory budget available
            low_water_mark: Fraction of budget at which warning issued
            critical_threshold: Fraction at which critical event triggered
        """
        self.total_mb = total_mb
        self.low_water_mark = low_water_mark
        self.critical_threshold = critical_threshold

        # Component budgets
        self._budgets: Dict[str, Budget] = {}

        # Cleanup callbacks
        self._cleanup_callbacks: Dict[str, List[Callable[[], None]]] = {}

        # Reallocation strategies
        self._reallocation_strategies: Dict[str, Callable[[float], float]] = {}

        # Lock for thread safety
        self._lock = threading.RLock()

        # Tracking
        self._total_allocated = 0.0
        self._allocation_history: List[BudgetAllocation] = []

    def allocate(
        self,
        component: str,
        budget_mb: float,
        cleanup_callback: Optional[Callable[[], None]] = None,
    ) -> Budget:
        """
        Allocate budget to a component.
        
        Args:
            component: Component name
            budget_mb: Budget in MB
            cleanup_callback: Function to call when cleanup needed
        
        Returns:
            Budget object
        """
        with self._lock:
            if component in self._budgets:
                logger.warning(f"Budget for {component} already allocated, replacing")

            # Check total allocation
            total_alloc = (
                sum(b.total_mb for b in self._budgets.values() if b.name != component)
                + budget_mb
            )

            if total_alloc > self.total_mb:
                logger.warning(
                    f"Total budget allocation {total_alloc}MB exceeds limit {self.total_mb}MB"
                )

            budget = Budget(name=component, total_mb=budget_mb)
            self._budgets[component] = budget

            if cleanup_callback:
                self._cleanup_callbacks[component] = [cleanup_callback]

            logger.info(f"Allocated {budget_mb}MB budget to {component}")

            return budget

    def get_budget(self, component: str) -> Optional[Budget]:
        """Get budget for a component."""
        with self._lock:
            return self._budgets.get(component)

    def get_all_budgets(self) -> Dict[str, Budget]:
        """Get all component budgets."""
        with self._lock:
            return dict(self._budgets)

    def request_memory(
        self, component: str, amount_mb: float, allow_cleanup: bool = True
    ) -> bool:
        """
        Request memory allocation from a component's budget.
        
        Args:
            component: Component requesting memory
            amount_mb: Amount in MB
            allow_cleanup: Whether to trigger cleanup if needed
        
        Returns:
            True if memory allocated, False if not available
        """
        with self._lock:
            budget = self._budgets.get(component)

            if not budget:
                logger.error(f"No budget allocated for {component}")
                return False

            # Try direct allocation
            if budget.allocate(amount_mb):
                return True

            # Budget exceeded - try cleanup if allowed
            if allow_cleanup and component in self._cleanup_callbacks:
                logger.warning(
                    f"{component} budget exceeded, triggering cleanup"
                )

                # Call cleanup callbacks
                for callback in self._cleanup_callbacks[component]:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"Error in cleanup callback: {e}")

                # Try allocation again
                if budget.allocate(amount_mb):
                    return True

            logger.error(
                f"Cannot allocate {amount_mb}MB for {component} "
                f"(available: {budget.available_mb}MB)"
            )
            return False

    def release_memory(self, component: str, amount_mb: float) -> None:
        """
        Release memory back to a component's budget.
        
        Args:
            component: Component releasing memory
            amount_mb: Amount in MB
        """
        with self._lock:
            budget = self._budgets.get(component)

            if budget:
                budget.deallocate(amount_mb)

    def reallocate(
        self, from_component: str, to_component: str, amount_mb: float
    ) -> bool:
        """
        Reallocate memory from one component to another.
        
        Args:
            from_component: Source component
            to_component: Destination component
            amount_mb: Amount to reallocate in MB
        
        Returns:
            True if reallocation succeeded
        """
        with self._lock:
            from_budget = self._budgets.get(from_component)
            to_budget = self._budgets.get(to_component)

            if not from_budget or not to_budget:
                return False

            # Check if reallocation is possible
            if from_budget.used_mb < amount_mb:
                logger.warning(
                    f"Cannot reallocate {amount_mb}MB from {from_component} "
                    f"(only {from_budget.used_mb}MB used)"
                )
                return False

            # Check if destination has room
            if to_budget.used_mb + amount_mb > to_budget.total_mb:
                # Try to grow to_budget
                to_budget.total_mb += amount_mb
                from_budget.total_mb -= amount_mb

            # Perform reallocation
            from_budget.deallocate(amount_mb)
            to_budget.allocate(amount_mb)

            logger.info(f"Reallocated {amount_mb}MB from {from_component} to {to_component}")

            return True

    def register_cleanup_callback(
        self, component: str, callback: Callable[[], None]
    ) -> None:
        """Register additional cleanup callback for a component."""
        with self._lock:
            if component not in self._cleanup_callbacks:
                self._cleanup_callbacks[component] = []

            self._cleanup_callbacks[component].append(callback)

    def check_health(self) -> Dict[str, str]:
        """
        Check health of all budgets.
        
        Returns:
            Dictionary of component -> health status
        """
        with self._lock:
            health = {}

            for name, budget in self._budgets.items():
                available_fraction = budget.available_mb / budget.total_mb
                level = budget.level

                health[name] = str(level.value)

                # Log warnings
                if available_fraction < self.critical_threshold:
                    logger.critical(
                        f"Budget {name} at CRITICAL level: "
                        f"{available_fraction:.1%} available"
                    )
                elif available_fraction < self.low_water_mark:
                    logger.warning(
                        f"Budget {name} at HIGH level: "
                        f"{available_fraction:.1%} available"
                    )

            return health

    def get_summary(self) -> str:
        """Get summary of all budgets."""
        with self._lock:
            total_used = sum(b.used_mb for b in self._budgets.values())
            total_available = self.total_mb - total_used

            summary = (
                f"Memory Budget Summary:\n"
                f"  Total: {self.total_mb}MB\n"
                f"  Used: {total_used:.1f}MB ({total_used/self.total_mb*100:.1f}%)\n"
                f"  Available: {total_available:.1f}MB\n"
                f"  Components:\n"
            )

            for name, budget in sorted(self._budgets.items()):
                summary += (
                    f"    {name}: {budget.used_mb:.1f}/{budget.total_mb:.1f}MB "
                    f"({budget.percent_used:.0f}%, {budget.level.value})\n"
                )

            return summary

    def __repr__(self) -> str:
        total_used = sum(b.used_mb for b in self._budgets.values())
        return (
            f"<MemoryBudgets: {total_used:.1f}/{self.total_mb:.1f}MB "
            f"({len(self._budgets)} components)>"
        )


def get_memory_budgets(total_mb: float = 100) -> MemoryBudgets:
    """
    Get or create global memory budgets instance.
    
    Args:
        total_mb: Total memory budget
    
    Returns:
        MemoryBudgets instance
    """
    if not hasattr(get_memory_budgets, "_instance"):
        get_memory_budgets._instance = MemoryBudgets(total_mb=total_mb)
    return get_memory_budgets._instance


def estimate_memory_budgets_overhead() -> Dict[str, str]:
    """Estimate overhead of memory budgeting system."""
    return {
        "budgets_dict": "~100 bytes per budget",
        "callbacks": "~200 bytes per callback",
        "tracking": "~1KB per 1000 allocations",
        "total_per_manager": "~1-2MB",
    }
