"""Task scheduler for autonomous periodic actions (heartbeat system)."""

import re
import asyncio
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class CronParser:
    """Simple cron expression parser."""
    
    @staticmethod
    def parse(expression: str) -> Dict[str, List[int]]:
        """Parse cron expression into minute, hour, day, month, weekday.
        
        Args:
            expression: Cron expression (e.g., "0 9 * * *")
            
        Returns:
            Dictionary with parsed values
        """
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError("Invalid cron expression: must have 5 fields")
        
        minute = CronParser._parse_field(parts[0], 0, 59)
        hour = CronParser._parse_field(parts[1], 0, 23)
        day = CronParser._parse_field(parts[2], 1, 31)
        month = CronParser._parse_field(parts[3], 1, 12)
        weekday = CronParser._parse_field(parts[4], 0, 6)
        
        return {
            'minute': minute,
            'hour': hour,
            'day': day,
            'month': month,
            'weekday': weekday,
        }
    
    @staticmethod
    def _parse_field(field: str, min_val: int, max_val: int) -> List[int]:
        """Parse a single cron field.
        
        Args:
            field: Field string (e.g., "0", "*/5", "1-5", "1,2,3")
            min_val: Minimum valid value
            max_val: Maximum valid value
            
        Returns:
            List of valid values
        """
        if field == '*':
            return list(range(min_val, max_val + 1))
        
        if '/' in field:
            # Handle step values (e.g., "*/5", "0-30/5")
            if field.startswith('*/'):
                step = int(field[2:])
                return list(range(min_val, max_val + 1, step))
            else:
                # Range with step (e.g., "0-30/5")
                parts = field.split('/')
                range_parts = parts[0].split('-')
                start = int(range_parts[0])
                end = int(range_parts[1]) if len(range_parts) > 1 else max_val
                step = int(parts[1])
                return list(range(start, end + 1, step))
        
        if '-' in field:
            # Handle ranges (e.g., "1-5")
            start, end = field.split('-')
            return list(range(int(start), int(end) + 1))
        
        if ',' in field:
            # Handle lists (e.g., "1,2,3")
            return [int(x) for x in field.split(',')]
        
        # Single value
        return [int(field)]
    
    @staticmethod
    def should_run(cron_parsed: Dict[str, List[int]], dt: datetime) -> bool:
        """Check if task should run at given time.
        
        Args:
            cron_parsed: Parsed cron expression from parse()
            dt: Datetime to check
            
        Returns:
            True if task should run
        """
        return (
            dt.minute in cron_parsed['minute'] and
            dt.hour in cron_parsed['hour'] and
            dt.day in cron_parsed['day'] and
            dt.month in cron_parsed['month'] and
            dt.weekday() in cron_parsed['weekday']
        )


class Task:
    """A scheduled task."""
    
    def __init__(
        self,
        name: str,
        schedule: str,
        action: str,
        enabled: bool = True,
        **kwargs
    ):
        """Initialize task.
        
        Args:
            name: Task name
            schedule: Cron schedule expression
            action: Task action type (send_to_channel, run_tool, execute_script)
            enabled: Whether task is enabled
            **kwargs: Additional task parameters
        """
        self.name = name
        self.schedule = schedule
        self.action = action
        self.enabled = enabled
        self.params = kwargs
        
        # Parse schedule
        try:
            self.cron_parsed = CronParser.parse(schedule)
        except ValueError as e:
            logger.error(f"Invalid cron schedule for task {name}: {e}")
            self.cron_parsed = None
        
        # Execution tracking
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.execution_count = 0
        self.last_error: Optional[str] = None
    
    def should_run(self, dt: datetime) -> bool:
        """Check if task should run at given time.
        
        Args:
            dt: Datetime to check
            
        Returns:
            True if task should run and is enabled
        """
        if not self.enabled or not self.cron_parsed:
            return False
        
        # Prevent duplicate runs in the same minute
        if self.last_run and self.last_run.replace(second=0, microsecond=0) == dt.replace(second=0, microsecond=0):
            return False
        
        return CronParser.should_run(self.cron_parsed, dt)
    
    async def execute(self, executor: Optional[Callable] = None) -> bool:
        """Execute the task.
        
        Args:
            executor: Callable to execute the task (executor(task) -> result)
            
        Returns:
            True if successful
        """
        try:
            if not executor:
                logger.warning(f"No executor provided for task: {self.name}")
                return False
            
            result = await executor(self)
            self.last_run = datetime.now()
            self.execution_count += 1
            self.last_error = None
            logger.info(f"Task executed: {self.name}")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Task failed: {self.name}: {e}")
            return False
    
    def __repr__(self) -> str:
        status = "✓" if self.enabled else "✗"
        return f"[{status}] {self.name} ({self.schedule})"


class TaskScheduler:
    """Scheduler for autonomous periodic tasks."""
    
    def __init__(self, heartbeat_file: Optional[str] = None):
        """Initialize scheduler.
        
        Args:
            heartbeat_file: Path to HEARTBEAT.md file
        """
        if heartbeat_file is None:
            heartbeat_file = str(Path.cwd() / 'workspace' / 'HEARTBEAT.md')
        
        self.heartbeat_file = Path(heartbeat_file)
        self.tasks: Dict[str, Task] = {}
        self.executor: Optional[Callable] = None
        self.is_running = False
        self._load_tasks()
    
    def _load_tasks(self):
        """Load tasks from HEARTBEAT.md file."""
        if not self.heartbeat_file.exists():
            logger.warning(f"Heartbeat file not found: {self.heartbeat_file}")
            return
        
        try:
            content = self.heartbeat_file.read_text()
            self.tasks = self._parse_heartbeat(content)
            logger.info(f"Loaded {len(self.tasks)} tasks from {self.heartbeat_file}")
        except Exception as e:
            logger.error(f"Failed to load heartbeat file: {e}")
    
    def _parse_heartbeat(self, content: str) -> Dict[str, Task]:
        """Parse HEARTBEAT.md and extract tasks.
        
        Args:
            content: File content
            
        Returns:
            Dictionary of Task objects keyed by task name
        """
        tasks = {}
        
        # Simple YAML-like parsing for task blocks
        # Looking for patterns like:
        # task_name: "..."
        # schedule: "..."
        # enabled: true/false
        # action: "..."
        
        task_blocks = []
        current_block = []
        
        for line in content.split('\n'):
            # Start new block if we see a task_name line
            if line.strip().startswith('task_name:'):
                if current_block:
                    task_blocks.append('\n'.join(current_block))
                current_block = [line]
            elif current_block and line.strip() and not line.startswith('##'):
                current_block.append(line)
            elif current_block and not line.strip():
                # Empty line might be end of task
                continue
        
        if current_block:
            task_blocks.append('\n'.join(current_block))
        
        # Parse each task block
        for block in task_blocks:
            try:
                task = self._parse_task_block(block)
                if task:
                    tasks[task.name] = task
            except Exception as e:
                logger.error(f"Error parsing task block: {e}")
        
        return tasks
    
    def _parse_task_block(self, block: str) -> Optional[Task]:
        """Parse a single task block.
        
        Args:
            block: Task block content
            
        Returns:
            Task object or None if invalid
        """
        # Extract fields using simple regex
        fields = {}
        
        for line in block.split('\n'):
            if ':' not in line:
                continue
            
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Remove quotes
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            
            # Parse booleans
            if value.lower() in ('true', 'false', 'yes', 'no'):
                value = value.lower() in ('true', 'yes')
            
            fields[key] = value
        
        if 'task_name' not in fields or 'schedule' not in fields or 'action' not in fields:
            return None
        
        return Task(
            name=fields['task_name'],
            schedule=fields['schedule'],
            action=fields['action'],
            enabled=fields.get('enabled', True),
            **{k: v for k, v in fields.items() if k not in ['task_name', 'schedule', 'action', 'enabled']}
        )
    
    async def start(self, executor: Callable):
        """Start the scheduler.
        
        Args:
            executor: Coroutine to execute each task (executor(task) -> result)
        """
        self.executor = executor
        self.is_running = True
        logger.info("Task scheduler started")
        
        # Main scheduler loop
        while self.is_running:
            try:
                now = datetime.now()
                
                # Check each task
                for task_name, task in self.tasks.items():
                    if task.should_run(now):
                        # Execute task asynchronously
                        asyncio.create_task(task.execute(executor))
                
                # Check every minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        logger.info("Task scheduler stopped")
    
    def get_tasks(self) -> List[Task]:
        """Get all tasks.
        
        Returns:
            List of Task objects
        """
        return list(self.tasks.values())
    
    def get_task(self, name: str) -> Optional[Task]:
        """Get a specific task by name.
        
        Args:
            name: Task name
            
        Returns:
            Task object or None
        """
        return self.tasks.get(name)
    
    def enable_task(self, name: str):
        """Enable a task.
        
        Args:
            name: Task name
        """
        if name in self.tasks:
            self.tasks[name].enabled = True
    
    def disable_task(self, name: str):
        """Disable a task.
        
        Args:
            name: Task name
        """
        if name in self.tasks:
            self.tasks[name].enabled = False
    
    def reload_tasks(self):
        """Reload tasks from HEARTBEAT.md."""
        self._load_tasks()
