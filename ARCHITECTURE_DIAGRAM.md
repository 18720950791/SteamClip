# SteamClip Task Queue - Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SteamClipApp                                  │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  UI Buttons  │  │  Clip Grid   │  │   Task Queue Dialog      │  │
│  │              │  │              │  │                          │  │
│  │ [Convert]    │  │ [Thumbnail]  │  │  Summary: 5 tasks        │  │
│  │ [Export All] │  │ [Thumbnail]  │  │  ┌────────────────────┐ │  │
│  │ [View Queue] │  │ [Thumbnail]  │  │  │ # │ Name │ Status  │ │  │
│  └──────┬───────┘  └──────────────┘  │  │ 1 │ Clip1│ ✓ OK    │ │  │
│         │                            │  │ 2 │ Clip2│ ⚙ 45%   │ │  │
│         │                            │  │ 3 │ Clip3│ ⏳ Wait  │ │  │
│         │                            │  │ 4 │ Clip4│ ✗ Fail  │ │  │
│         │                            │  └────────────────────┘ │  │
│         │                            │  [Cancel] [Remove] [Retry]│  │
│         │                            └──────────────────────────┘  │
│         │                                     ▲                     │
│         └─────────────────────────────────────┘                     │
│                         controls                                    │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Task Queue Manager                          │  │
│  │                                                                │  │
│  │  self.task_queue = TaskQueue()                                │  │
│  │  self.conversion_worker = ConversionWorker(...)               │  │
│  │  self.task_queue_dialog = TaskQueueDialog(...)                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
User Action Flow:
═══════════════════════════════════════════════════════════════════

1. User selects clips
   └─> self.selected_clips = {"/clip1", "/clip2", ...}

2. User clicks "Convert Clip(s)"
   └─> convert_clip()
       └─> process_clips(selected_clips=...)

3. process_clips()
   ├─> validate_export_directory()
   ├─> get_clips_to_process()
   ├─> Create TaskQueue
   │   └─> task_queue.add_tasks(clip_list)
   │       └─> [ConversionTask, ConversionTask, ...]
   ├─> Show TaskQueueDialog
   └─> _start_worker()
       └─> ConversionWorker(task_queue, ...)
           └─> worker.start()

4. ConversionWorker.run()
   ┌──────────────────────────────────────────────────────────┐
   │ while queue.has_waiting():                                │
   │   task = queue.get_next_waiting()                        │
   │   task.status = PROCESSING                               │
   │   emit task_started(task.id)                             │
   │                                                          │
   │   try:                                                   │
   │     output = _process_task(task)                         │
   │     task.status = SUCCESS                                │
   │     task.output_path = output                            │
   │     emit task_completed(task.id, output)                 │
   │   except Exception as e:                                 │
   │     task.status = FAILED                                 │
   │     task.error_message = str(e)                          │
   │     emit task_failed(task.id, str(e))                    │
   │                                                          │
   │ emit queue_finished(stats)                               │
   └──────────────────────────────────────────────────────────┘

5. Signal Handlers
   ├─> on_worker_task_started()
   │   └─> dialog.on_task_started()
   │       └─> Update progress bar, scroll to task
   │
   ├─> on_worker_task_progress()
   │   └─> dialog.on_task_progress()
   │       └─> Update progress percentage
   │
   ├─> on_worker_task_completed()
   │   └─> dialog.on_task_completed()
   │       └─> Refresh table, show output path
   │
   ├─> on_worker_task_failed()
   │   └─> dialog.on_task_failed()
   │       └─> Refresh table, show error
   │
   └─> on_worker_queue_finished()
       └─> dialog.on_queue_finished()
           └─> Show summary dialog with results
```

## Task State Machine

```
                    ┌─────────────┐
                    │   WAITING   │
                    └──────┬──────┘
                           │
                    get_next_waiting()
                           │
                    ┌──────▼──────┐
              ┌────>│ PROCESSING  │<────┐
              │     └──────┬──────┘     │
              │            │            │
              │     ┌──────┴──────┐     │
              │     │             │     │
         success   fail      cancel   retry
              │     │             │     │
              │     │             │     │
    ┌─────────▼─┐  ┌▼────────┐  ┌▼──────────┐
    │  SUCCESS  │  │  FAILED │  │ CANCELLED │
    └───────────┘  └────┬────┘  └───────────┘
                        │
                   retry_failed()
                        │
                        └────────> WAITING
```

## Component Interactions

```
┌────────────────────────────────────────────────────────────────────┐
│                     Signal Flow Diagram                             │
└────────────────────────────────────────────────────────────────────┘

ConversionWorker                    SteamClipApp                    TaskQueueDialog
─────────────────                   ──────────────                  ─────────────────

task_started(task_id) ────────────> on_worker_task_started()
                                    │
                                    └────────────────────────────> on_task_started()
                                                                   │
                                                                   └─> Update UI

task_progress(id, msg, %) ────────> on_worker_task_progress()
                                    │
                                    └────────────────────────────> on_task_progress()
                                                                   │
                                                                   └─> Update progress bar

task_completed(id, path) ─────────> on_worker_task_completed()
                                    │
                                    └────────────────────────────> on_task_completed()
                                                                   │
                                                                   └─> Refresh table

task_failed(id, error) ───────────> on_worker_task_failed()
                                    │
                                    └────────────────────────────> on_task_failed()
                                                                   │
                                                                   └─> Show error

queue_finished(stats) ────────────> on_worker_queue_finished()
                                    │
                                    ├─> toggle_interface(True)
                                    │
                                    └────────────────────────────> on_queue_finished()
                                                                   │
                                                                   └─> Show summary

                                    <──────────────────────────── retry_requested
                                    │
                                    └─> on_retry_requested()
                                        │
                                        └─> _start_worker()
```

## Class Hierarchy

```
QThread
  ├─> ConversionThread (original, retained for compatibility)
  └─> ConversionWorker (new, task queue based)
        └─> Processes ConversionTask objects from TaskQueue

QDialog
  └─> TaskQueueDialog (new)
        └─> Displays TaskQueue status and controls

QObject
  └─> TaskQueue (new)
        └─> Manages List[ConversionTask]

Enum
  └─> TaskStatus (new)
        └─> WAITING | PROCESSING | SUCCESS | FAILED | CANCELLED

Dataclass
  └─> ConversionTask (new)
        └─> id, clip_folder, status, output_path, error_message
```

## Threading Model

```
Main Thread (UI)                    Worker Thread (ConversionWorker)
────────────────                    ────────────────────────────────

User clicks "Convert"
  │
  ├─> Create TaskQueue
  ├─> Show Dialog
  ├─> Create Worker
  └─> worker.start() ─────────────> run()
                                    │
                                    ├─> Process task 1
                                    │   ├─> emit task_started
                                    │   ├─> emit task_progress (multiple)
                                    │   └─> emit task_completed
                                    │
                                    ├─> Process task 2
                                    │   ├─> emit task_started
                                    │   ├─> emit task_progress (multiple)
                                    │   └─> emit task_failed
                                    │
                                    ├─> Process task 3
                                    │   └─> ...
                                    │
                                    └─> emit queue_finished
  <────────────────────────────────   return

on_worker_task_started() <───────── (signal)
  └─> Update dialog UI

on_worker_task_completed() <─────── (signal)
  └─> Update dialog UI

on_worker_queue_finished() <─────── (signal)
  ├─> Re-enable UI
  └─> Show summary

Worker thread exits <────────────── (finished signal)
  └─> Cleanup
```

## Error Handling Flow

```
Task Processing Error:
═════════════════════

_process_task(task)
  │
  ├─> Find session.mpd files
  │   └─> FileNotFoundError ──┐
  │                           │
  ├─> Prepare temp media      │
  │   └─> FileNotFoundError ──┤
  │                           │
  ├─> Concatenate video       │
  │   └─> subprocess.CalledProcessError ──┤
  │                           │
  ├─> Concatenate audio       │
  │   └─> subprocess.CalledProcessError ──┤
  │                           │
  └─> Merge final output      │
      └─> subprocess.CalledProcessError ──┤
                                          │
                                          ▼
                                    except Exception as e:
                                      task.status = FAILED
                                      task.error_message = str(e)
                                      emit task_failed(id, error)
                                      │
                                      └─> Continue to next task
                                          (queue continues)

finally:
  _cleanup_temp_files()
  └─> Always cleanup, even on error
```

## UI Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  SteamClip                                                            │
├─────────────────────────────────────────────────────────────────────┤
│  [⚙ Settings]  [SteamID ▼]  [Game ID ▼]  [Media Type ▼]            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│  │ Clip 1   │  │ Clip 2   │  │ Clip 3   │  ← Selected clips       │
│  │ (blue)   │  │ (blue)   │  │ (blue)   │                          │
│  └──────────┘  └──────────┘  └──────────┘                          │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│              [Clear Selection]  [Export All]                         │
├─────────────────────────────────────────────────────────────────────┤
│  [<< Prev]  [Next >>]  [Convert Clip(s)]  [View Queue]  [Exit]     │
├─────────────────────────────────────────────────────────────────────┤
│  ████████████░░░░░░░░  Processing Clip 2/5 - 45%                    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Conversion Queue                                          [X]        │
├─────────────────────────────────────────────────────────────────────┤
│  Total: 5  |  Waiting: 2  |  Processing: 1  |  Success: 1  |       │
│  Failed: 1  |  Cancelled: 0                                         │
├─────────────────────────────────────────────────────────────────────┤
│  ████████████░░░░░░░░  Concatenating video (45%)                    │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ # │ Clip Name              │ Status      │ Output / Error    │  │
│  ├───┼────────────────────────┼─────────────┼───────────────────┤  │
│  │ 1 │ Game_2024-01-01_12-00  │ ✓ Success   │ /out/Game_1.mp4   │  │
│  │ 2 │ Game_2024-01-01_12-05  │ ⚙ Processing│                   │  │
│  │ 3 │ Game_2024-01-01_12-10  │ ⏳ Waiting   │                   │  │
│  │ 4 │ Game_2024-01-01_12-15  │ ⏳ Waiting   │                   │  │
│  │ 5 │ Game_2024-01-01_12-20  │ ✗ Failed    │ FFmpeg error      │  │
│  └──────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  [Cancel Current]  [Remove All Pending]  [Retry Failed]            │
│  [Open Output Folder]                                    [Close]   │
└─────────────────────────────────────────────────────────────────────┘
```

## Summary

The task queue system provides:
- **Decoupled processing**: Worker thread handles all conversion logic
- **Real-time feedback**: Signals update UI as tasks progress
- **Flexible control**: Cancel, remove, retry operations
- **Error resilience**: Failures don't stop the queue
- **User-friendly**: Visual status tracking and results summary

All components work together seamlessly to provide a robust, scalable conversion workflow.
