# Light Automation Implementation Plan (Wasp-in-a-Box)

This document details the tasks and file modifications required to implement a robust, automatic lighting system using the "Wasp-in-a-Box" algorithm. This approach filters out radar false negatives (when a person is stationary) by correlating motion events with door events.

## 1. Update `core/state.py`
Add variables to track the logical occupancy state and thresholds.

**Modifications:**
- Add `is_occupied: bool = False` to `BuddyState`.
- Initialize `last_presence` and `last_door_closed` properly (ensure they default to `None` instead of `time.time()` at load time, to avoid incorrect logical deductions on startup).
- Define a threshold for luminance, either as a state property or constant. E.g., `luminance_threshold_dark: int = 300` (adjust value based on sensor specs).

## 2. Update `core/brain.py` (Event Handlers)
Modify the `BuddyBrain` class to implement the Wasp-in-a-Box logic.

### Modifying `_handle_presence_input(self, event)`:

**When `event.content is True` (Presence Detected):**
1. Update `global_state.last_presence = time.time()`.
2. Check if the house was previously empty: `if not global_state.is_occupied:`
   - Set `global_state.is_occupied = True`.
   - Check if it's dark: `if global_state.luminance is not None and global_state.luminance < global_state.luminance_threshold_dark:`
   - Generate and return an `OutputEvent` to turn ON the lights.
3. *If the house was already occupied, do nothing regarding lights (so we don't accidentally turn them back on if the user manually turned them off to watch a movie).*

**When `event.content is False` (Absence Detected):**
1. Update `global_state.last_absence = time.time()`.
2. Apply Wasp-in-a-Box logic to determine if the person actually left:
   - Check if `global_state.is_door_closed` is True.
   - Check if `global_state.last_door_closed > global_state.last_presence`.
   - *(Explanation: If the door was closed AFTER the last detected movement, and the radar now sees nobody, it means the person walked out and closed the door behind them).*
3. If the above condition is True AND `global_state.is_occupied` is True:
   - Set `global_state.is_occupied = False`.
   - Generate and return an `OutputEvent` to turn OFF the lights.

### Modifying `_handle_door_input(self, event)`:
**When `event.content is True` (Door Closed):**
1. Update `global_state.last_door_closed = time.time()`.
2. Ensure `global_state.is_door_closed = True`.

**When `event.content is False` (Door Opened):**
1. Ensure `global_state.is_door_closed = False`.

## 3. Testing and Validation
- Verify that sitting still (radar sending `False`) while the door hasn't been opened does NOT turn off the lights.
- Verify that entering a dark room correctly triggers the lights.
- Verify that leaving the room (door open -> close -> radar absence) correctly turns off the lights.