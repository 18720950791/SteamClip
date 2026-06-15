# SteamClip Task Queue Feature

## Overview

The conversion workflow has been extended with a task queue system that allows processing multiple clips sequentially with detailed status tracking, cancellation support, and retry capabilities.

## Features

### 1. Multi-Task Submission
- Submit multiple clips for conversion at once (via "Convert Clip(s)" or "Export All")
- All clips are added to a queue and processed sequentially
- No more blocking the entire UI during batch conversions

### 2. Real-Time Status Tracking
Each task displays one of five status states:
- **⏳ Waiting** - Task is queued and waiting to be processed
- **⚙ Processing...** - Task is currently being converted (with progress bar)
- **✓ Success** - Task completed successfully (shows output path)
- **✗ Failed** - Task failed (shows error message)
- **⊘ Cancelled** - Task was cancelled by user

### 3. Task Queue Dialog
The queue dialog provides:
- **Summary bar** showing counts of tasks in each state
- **Progress bar** for the currently processing task
- **Task table** with columns: #, Clip Name, Status, Output/Error
- **Color-coded status** for easy visual identification
- **Action buttons**:
  - **Cancel Current** - Cancel the currently processing task
  - **Remove All Pending** - Remove all waiting tasks from the queue
  - **Retry Failed** - Re-queue all failed tasks (only shown after queue finishes)
  - **Open Output Folder** - Open the folder containing successful conversions
  - **Close** - Close the dialog (processing continues in background)

### 4. Cancellation Support
- **Cancel current task**: Stops the current conversion and moves to the next task
- **Remove pending tasks**: Removes all waiting tasks from the queue
- **Stop all**: Cancels current task and marks all remaining tasks as cancelled

### 5. Failure Resilience
- If a task fails, the queue continues processing remaining tasks
- Failed tasks are marked with error messages
- After queue completion, failed tasks can be retried with one click

### 6. Results Summary
When all tasks complete, a summary dialog shows:
- Total count of successful, failed, and cancelled tasks
- List of successful conversions with output paths
- List of failed conversions with error messages

## Usage

### Basic Workflow

1. **Select clips** by clicking thumbnails (blue border indicates selection)
2. **Click "Convert Clip(s)"** or **"Export All"**
3. **Task Queue Dialog opens automatically** showing all queued tasks
4. **Monitor progress** in real-time:
   - Current task shows progress bar
   - Status updates as tasks complete or fail
5. **Take actions** as needed:
   - Cancel current task if needed
   - Remove pending tasks to stop queue
   - Close dialog to continue processing in background

### Viewing Queue Status

- **"View Queue" button** in the bottom toolbar opens the queue dialog
- Button is enabled only when there's an active queue
- Useful if you closed the dialog and want to check progress

### Retrying Failed Tasks

1. Wait for queue to finish
2. **"Retry Failed" button** appears if any tasks failed
3. Click to re-queue all failed tasks
4. Queue automatically restarts processing the retried tasks

### Accessing Output Files

1. After successful conversions, click **"Open Output Folder"**
2. File manager opens to the export directory
3. Find your converted clips named: `{GameName}_{YYYY-MM-DD_HH-MM-SS}.mp4`

## Technical Details

### Architecture

```
SteamClipApp
  ├── task_queue: TaskQueue
  │     └── tasks: List[ConversionTask]
  ├── conversion_worker: ConversionWorker (QThread)
  │     └── Processes tasks sequentially
  └── task_queue_dialog: TaskQueueDialog
        └── Displays status and handles user actions
```

### Data Models

```python
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
    status: TaskStatus
    output_path: Optional[str]
    error_message: Optional[str]
    created_at: datetime
```

### Signal Flow

```
User Action
  ↓
process_clips() creates TaskQueue
  ↓
TaskQueueDialog shown
  ↓
ConversionWorker started
  ↓
For each task:
  task_started → Dialog updates
  task_progress → Progress bar updates
  task_completed/failed → Dialog updates
  ↓
queue_finished → Summary shown
```

### Key Classes

- **TaskQueue**: Manages queue of ConversionTask objects
- **ConversionWorker**: QThread that processes tasks sequentially
- **TaskQueueDialog**: QDialog displaying queue status and controls
- **ConversionTask**: Dataclass representing a single conversion task

## Backward Compatibility

The original `ConversionThread` class is retained for backward compatibility but is no longer used by the main application. All conversions now go through the task queue system.

## Error Handling

Common error scenarios:
- **Missing session.mpd**: Task fails with "No session.mpd files found"
- **Missing init streams**: Task fails with "Initialization files missing"
- **FFmpeg errors**: Task fails with subprocess error details
- **User cancellation**: Task marked as cancelled, queue continues

All errors are logged to the application log and displayed in the queue dialog.

## Performance Considerations

- Tasks are processed sequentially to avoid overwhelming system resources
- Temp files are cleaned up after each task (success or failure)
- Progress updates are throttled to avoid UI lag
- Large batches (100+ clips) work smoothly

## Future Enhancements

Potential improvements:
- Parallel task processing (with configurable concurrency)
- Task priority ordering
- Persistent queue across app restarts
- Task scheduling (process at specific time)
- Detailed per-task logs
- Export queue to file
