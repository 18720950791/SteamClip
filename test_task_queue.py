#!/usr/bin/env python3
"""
Test script for SteamClip Task Queue functionality.
This script tests the TaskQueue and ConversionTask classes independently.
"""

import sys
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict
import uuid

# Inline the classes for testing (copied from steamclip.py)

class TaskStatus(Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ConversionTask:
    id: str
    clip_folder: str
    status: TaskStatus = TaskStatus.WAITING
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def clip_name(self) -> str:
        """Extract readable clip name from folder path."""
        import os
        return os.path.basename(self.clip_folder)

class TaskQueue:
    """Manages a queue of conversion tasks."""

    def __init__(self):
        self.tasks: List[ConversionTask] = []

    def add_tasks(self, clip_folders: List[str]) -> List[str]:
        """Add multiple tasks to the queue, return list of task IDs."""
        task_ids = []
        for folder in clip_folders:
            task = ConversionTask(
                id=str(uuid.uuid4())[:8],
                clip_folder=folder
            )
            self.tasks.append(task)
            task_ids.append(task.id)
        return task_ids

    def get_next_waiting(self) -> Optional[ConversionTask]:
        """Get the next waiting task, or None if all are processed."""
        for task in self.tasks:
            if task.status == TaskStatus.WAITING:
                return task
        return None

    def get_task(self, task_id: str) -> Optional[ConversionTask]:
        """Get a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def cancel_current(self) -> Optional[str]:
        """Cancel the currently processing task. Returns task ID or None."""
        for task in self.tasks:
            if task.status == TaskStatus.PROCESSING:
                task.status = TaskStatus.CANCELLED
                task.error_message = "Cancelled by user"
                return task.id
        return None

    def remove_waiting(self, task_id: str) -> bool:
        """Remove a waiting task from the queue."""
        for i, task in enumerate(self.tasks):
            if task.id == task_id and task.status == TaskStatus.WAITING:
                self.tasks.pop(i)
                return True
        return False

    def remove_all_waiting(self) -> int:
        """Remove all waiting tasks. Returns count removed."""
        waiting = [t for t in self.tasks if t.status == TaskStatus.WAITING]
        self.tasks = [t for t in self.tasks if t.status != TaskStatus.WAITING]
        return len(waiting)

    def retry_failed(self) -> List[str]:
        """Reset all failed tasks to waiting status. Returns list of task IDs."""
        retried = []
        for task in self.tasks:
            if task.status == TaskStatus.FAILED:
                task.status = TaskStatus.WAITING
                task.error_message = None
                task.output_path = None
                retried.append(task.id)
        return retried

    def get_all_tasks(self) -> List[ConversionTask]:
        """Get all tasks in queue order."""
        return list(self.tasks)

    def get_stats(self) -> Dict[str, int]:
        """Get counts of tasks by status."""
        stats = {status.value: 0 for status in TaskStatus}
        for task in self.tasks:
            stats[task.status.value] += 1
        return stats

    def is_finished(self) -> bool:
        """Check if all tasks are in a terminal state."""
        terminal = {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED}
        return all(task.status in terminal for task in self.tasks)

    def has_waiting(self) -> bool:
        """Check if there are any waiting tasks."""
        return any(t.status == TaskStatus.WAITING for t in self.tasks)

    def has_failed(self) -> bool:
        """Check if there are any failed tasks."""
        return any(t.status == TaskStatus.FAILED for t in self.tasks)


# Test functions

def test_task_creation():
    """Test creating conversion tasks."""
    print("Testing task creation...")
    task = ConversionTask(
        id="test123",
        clip_folder="/path/to/clip_12345_20240101_120000"
    )
    assert task.id == "test123"
    assert task.status == TaskStatus.WAITING
    assert task.output_path is None
    assert task.error_message is None
    assert task.clip_name() == "clip_12345_20240101_120000"
    print("[OK] Task creation works correctly")

def test_task_queue():
    """Test TaskQueue operations."""
    print("\nTesting TaskQueue operations...")

    # Create queue and add tasks
    queue = TaskQueue()
    clip_folders = [
        "/path/to/clip1",
        "/path/to/clip2",
        "/path/to/clip3",
        "/path/to/clip4",
        "/path/to/clip5"
    ]
    task_ids = queue.add_tasks(clip_folders)
    assert len(task_ids) == 5
    assert len(queue.tasks) == 5
    print(f"[OK] Added {len(task_ids)} tasks to queue")

    # Get stats
    stats = queue.get_stats()
    assert stats['waiting'] == 5
    assert stats['processing'] == 0
    print(f"[OK] Initial stats: {stats}")

    # Get next waiting task
    task = queue.get_next_waiting()
    assert task is not None
    assert task.status == TaskStatus.WAITING
    print(f"[OK] Got next waiting task: {task.clip_name()}")

    # Simulate processing
    task.status = TaskStatus.PROCESSING
    assert queue.get_stats()['processing'] == 1
    print("[OK] Task marked as processing")

    # Complete task
    task.status = TaskStatus.SUCCESS
    task.output_path = "/output/clip1.mp4"
    print("[OK] Task completed successfully")

    # Fail a task
    task2 = queue.get_next_waiting()
    task2.status = TaskStatus.PROCESSING
    task2.status = TaskStatus.FAILED
    task2.error_message = "Test error"
    print("[OK] Task failed with error")

    # Cancel a task
    task3 = queue.get_next_waiting()
    cancelled_id = queue.cancel_current()
    assert cancelled_id is None  # No task is currently processing
    task3.status = TaskStatus.PROCESSING
    cancelled_id = queue.cancel_current()
    assert cancelled_id == task3.id
    print("[OK] Task cancelled")

    # Check stats
    stats = queue.get_stats()
    print(f"[OK] Current stats: {stats}")
    assert stats['success'] == 1
    assert stats['failed'] == 1
    assert stats['cancelled'] == 1
    assert stats['waiting'] == 2

    # Remove waiting tasks
    count = queue.remove_all_waiting()
    assert count == 2
    print(f"[OK] Removed {count} waiting tasks")

    # Check if queue is finished
    assert queue.is_finished()
    print("[OK] Queue is finished")

def test_retry_failed():
    """Test retrying failed tasks."""
    print("\nTesting retry functionality...")

    queue = TaskQueue()
    queue.add_tasks(["/clip1", "/clip2", "/clip3"])

    # Fail all tasks
    for task in queue.tasks:
        task.status = TaskStatus.FAILED
        task.error_message = "Test error"

    assert queue.has_failed()
    print("[OK] All tasks marked as failed")

    # Retry failed tasks
    retried = queue.retry_failed()
    assert len(retried) == 3
    assert all(task.status == TaskStatus.WAITING for task in queue.tasks)
    print(f"[OK] Retried {len(retried)} failed tasks")

    # Verify queue is not finished
    assert not queue.is_finished()
    assert queue.has_waiting()
    print("[OK] Queue ready for reprocessing")

def test_get_task():
    """Test getting task by ID."""
    print("\nTesting task retrieval...")

    queue = TaskQueue()
    task_ids = queue.add_tasks(["/clip1", "/clip2"])

    # Get task by ID
    task = queue.get_task(task_ids[0])
    assert task is not None
    assert task.id == task_ids[0]
    print(f"[OK] Retrieved task by ID: {task.id}")

    # Try to get non-existent task
    task = queue.get_task("nonexistent")
    assert task is None
    print("[OK] Returns None for non-existent task")

def test_remove_waiting():
    """Test removing individual waiting tasks."""
    print("\nTesting individual task removal...")

    queue = TaskQueue()
    task_ids = queue.add_tasks(["/clip1", "/clip2", "/clip3"])

    # Remove middle task
    removed = queue.remove_waiting(task_ids[1])
    assert removed
    assert len(queue.tasks) == 2
    print("[OK] Removed individual waiting task")

    # Try to remove non-existent task
    removed = queue.remove_waiting("nonexistent")
    assert not removed
    print("[OK] Returns False for non-existent task")

    # Try to remove processing task
    queue.tasks[0].status = TaskStatus.PROCESSING
    removed = queue.remove_waiting(task_ids[0])
    assert not removed
    print("[OK] Cannot remove processing task")

def test_queue_workflow():
    """Test a complete workflow scenario."""
    print("\nTesting complete workflow scenario...")

    queue = TaskQueue()

    # Add 5 clips
    clips = [f"/clips/game_clip{i}_{20240101}_{120000 + i}" for i in range(5)]
    task_ids = queue.add_tasks(clips)
    print(f"[OK] Added {len(clips)} clips to queue")

    # Process first 2 successfully
    for i in range(2):
        task = queue.get_next_waiting()
        task.status = TaskStatus.PROCESSING
        task.status = TaskStatus.SUCCESS
        task.output_path = f"/output/clip{i}.mp4"
    print("[OK] First 2 tasks completed successfully")

    # Fail the 3rd task
    task = queue.get_next_waiting()
    task.status = TaskStatus.PROCESSING
    task.status = TaskStatus.FAILED
    task.error_message = "FFmpeg error: corrupted file"
    print("[OK] 3rd task failed")

    # Process 4th successfully
    task = queue.get_next_waiting()
    task.status = TaskStatus.PROCESSING
    task.status = TaskStatus.SUCCESS
    task.output_path = "/output/clip3.mp4"
    print("[OK] 4th task completed successfully")

    # Cancel 5th task
    task = queue.get_next_waiting()
    task.status = TaskStatus.PROCESSING
    queue.cancel_current()
    print("[OK] 5th task cancelled")

    # Check final stats
    stats = queue.get_stats()
    assert stats['success'] == 3
    assert stats['failed'] == 1
    assert stats['cancelled'] == 1
    print(f"[OK] Final stats: {stats}")

    # Queue should be finished
    assert queue.is_finished()
    print("[OK] Queue is finished")

    # Retry failed task
    retried = queue.retry_failed()
    assert len(retried) == 1
    assert not queue.is_finished()
    assert queue.has_waiting()
    print(f"[OK] Retried {len(retried)} failed task(s)")

    # Process retried task successfully
    task = queue.get_next_waiting()
    task.status = TaskStatus.PROCESSING
    task.status = TaskStatus.SUCCESS
    task.output_path = "/output/clip2_retry.mp4"
    print("[OK] Retried task completed successfully")

    # Final check
    stats = queue.get_stats()
    assert stats['success'] == 4
    assert stats['failed'] == 0
    assert stats['cancelled'] == 1
    assert queue.is_finished()
    print(f"[OK] Final stats after retry: {stats}")

def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("SteamClip Task Queue Test Suite")
    print("=" * 60)

    try:
        test_task_creation()
        test_task_queue()
        test_retry_failed()
        test_get_task()
        test_remove_waiting()
        test_queue_workflow()

        print("\n" + "=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)
        print("\nSummary:")
        print("- Task creation and data model: OK")
        print("- Queue operations (add, get, cancel, remove): OK")
        print("- Retry failed tasks: OK")
        print("- Complete workflow scenario: OK")
        print("\nThe task queue system is ready for integration.")
        return 0
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
