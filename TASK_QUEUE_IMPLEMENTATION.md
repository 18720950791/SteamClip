# SteamClip Task Queue Implementation Plan

## Overview
Extend SteamClip's conversion workflow to support a task queue system that allows:
1. Submitting multiple conversion tasks at once
2. Displaying per-task status (waiting, processing, success, failed, cancelled)
3. Cancelling current task and removing pending tasks
4. Continuing on failure
5. Showing output paths and error summaries
6. Retrying only failed tasks

## Implementation

### 1. Data Models (add after imports, around line 50)

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
import uuid

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
```

### 2. TaskQueue Class (add after ConversionThread, around line 330)

```python
class TaskQueue:
    """Manages a queue of conversion tasks"""
    def __init__(self):
        self.tasks: List[ConversionTask] = []

    def add_tasks(self, clip_folders: List[str]) -> List[str]:
        """Add multiple tasks, return list of task IDs"""

    def cancel_current(self) -> bool:
        """Cancel the currently processing task"""

    def remove_waiting(self, task_id: str) -> bool:
        """Remove a waiting task from queue"""

    def get_current_task(self) -> Optional[ConversionTask]:
        """Get the currently processing task"""

    def get_waiting_tasks(self) -> List[ConversionTask]:
        """Get all waiting tasks"""

    def get_failed_tasks(self) -> List[ConversionTask]:
        """Get all failed tasks"""

    def retry_failed(self) -> List[str]:
        """Reset failed tasks to waiting, return their IDs"""

    def get_all_tasks(self) -> List[ConversionTask]:
        """Get all tasks in order"""
```

### 3. ConversionWorker (replace/modify ConversionThread, around line 136)

Extend ConversionThread to:
- Accept TaskQueue instead of clip_list
- Emit granular signals: task_started(task_id), task_completed(task_id, output_path), task_failed(task_id, error)
- Emit queue_finished(success_count, failed_count, cancelled_count)
- Process tasks sequentially, continuing on failure
- Support cancellation per-task

### 4. TaskQueueDialog (new QDialog, add after ConversionWorker)

```python
class TaskQueueDialog(QDialog):
    """Dialog showing task queue status and controls"""
    # UI elements:
    # - QTableWidget or QListWidget showing all tasks
    # - Columns: Task#, Clip Name, Status, Output/Error, Actions
    # - Progress bar for current task
    # - Buttons: Cancel Current, Remove All Pending, Retry Failed, Close
    # - Color coding for status
```

### 5. SteamClipApp Modifications

**Add instance variables (around line 360):**
- `self.task_queue = None`
- `self.conversion_worker = None`
- `self.task_queue_dialog = None`

**Modify convert_clip() (line 1462):**
- Create TaskQueue from selected_clips
- Show TaskQueueDialog
- Start ConversionWorker with queue

**Modify export_all() (line 1466):**
- Create TaskQueue from filtered clips
- Show TaskQueueDialog
- Start ConversionWorker with queue

**Add new methods:**
- `show_task_queue_dialog()` - display queue status
- `on_task_started(task_id)` - update dialog
- `on_task_completed(task_id, output_path)` - update dialog
- `on_task_failed(task_id, error)` - update dialog
- `on_queue_finished(stats)` - show summary

### 6. Signal Flow

```
User clicks "Convert Clip(s)" or "Export All"
  ↓
process_clips() creates TaskQueue with N tasks
  ↓
TaskQueueDialog shown with all tasks in WAITING status
  ↓
ConversionWorker started with queue
  ↓
For each task:
  - task_started signal → dialog updates status to PROCESSING
  - progress_update signal → dialog updates progress bar
  - task_completed/failed signal → dialog updates status
  ↓
queue_finished signal → dialog shows summary with retry option
```

## Files to Modify
- `steamclip.py` - all changes in this single file

## Lines Affected
- Add ~200 lines for new classes (TaskStatus, ConversionTask, TaskQueue, TaskQueueDialog)
- Modify ~50 lines in ConversionThread/ConversionWorker
- Modify ~30 lines in SteamClipApp methods
- Add ~50 lines for new SteamClipApp methods

Total: ~330 lines of changes/additions

## Testing Checklist
- [ ] Submit 1 clip - works as before
- [ ] Submit 5 clips - all process sequentially
- [ ] Cancel during processing - current task cancelled, rest continue
- [ ] Remove pending task - task removed from queue
- [ ] Force a failure (corrupt clip) - subsequent tasks still process
- [ ] All tasks complete - summary shows output paths
- [ ] Some tasks failed - summary shows errors, retry button works
- [ ] Retry failed - only failed tasks re-queued
- [ ] Close dialog during processing - continues in background
