from enum import Enum
import time
from datetime import datetime, timezone
from mukitodo import actions
from mukitodo.actions import Result, EmptyResult
from mukitodo.tui.states.message_holder import MessageHolder


class TimerStateEnum(Enum):
    """State of the timer."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"

class TimerPhaseEnum(Enum):
    """Phase of the NOW timer."""
    WORK = "work"
    BREAK = "break"

class TimerEventEnum(Enum):
    """One-shot timer events emitted by NowState and consumed by App layer."""
    WORK_5MIN_LEFT = "work_5min_left"
    WORK_TIME_UP = "work_time_up"
    BREAK_TIME_UP = "break_time_up"


class NowState:
    """State management for NOW view (action timer and session tracking).

    Manages:
    - Current item context (track/project/todo)
    - Timer state and countdown
    - Session tracking (for database persistence after confirmation)
    """

    def __init__(self, message_holder: MessageHolder):
        self._message = message_holder

        # == Item Context ==
        self._current_track_id: int | None = None
        self._current_project_id: int | None = None
        self._current_todo_id: int | None = None

        # Cached data for rendering (loaded from actions)
        self._current_project_dict: dict | None = None
        self._current_todo_dict: dict | None = None

        # == Timer State ==
        self._timer_state: TimerStateEnum = TimerStateEnum.IDLE
        self._target_minutes: int = 25
        self._remaining_seconds: int = 25 * 60
        self._timer_start_timestamp: float | None = None
        self._paused_remaining: int | None = None
        self._timer_phase: TimerPhaseEnum = TimerPhaseEnum.WORK
        self._pending_timer_event: TimerEventEnum | None = None
        self._work_warned_5min: bool = False
        # Work time-up latch: keep 00:00 and disable Space/adjust until reset or finish flow.
        self._work_timeup_latched: bool = False
        # Break is only prepared after finishing a time-up session flow.
        self._break_armed_after_finish: bool = False
        self._break_minutes_default: int = 5

        # == Session Tracking ==
        self._session_started_at: datetime | None = None  # For database persistence
        self._last_saved_session_id: int | None = None  # For session follow-up (e.g. description)


    # ========== Item Context Management ==========

    def set_item(self, track_id: int, project_id: int, todo_id: int | None) -> None:
        """Set the current item context for NOW view and load cached data."""
        self._current_track_id = track_id
        self._current_project_id = project_id
        self._current_todo_id = todo_id

        # Load and cache project data
        project_result = actions.get_project_dict(project_id)
        if project_result.success:
            self._current_project_dict = project_result.data
        else:
            self._current_project_dict = None

        # Load and cache todo data if provided
        if todo_id is not None:
            todo_result = actions.get_todo_dict(todo_id)
            if todo_result.success:
                self._current_todo_dict = todo_result.data
            else:
                self._current_todo_dict = None
        else:
            self._current_todo_dict = None

    def get_current_item_context(self) -> tuple[str, int | None, int | None, int | None]:
        """Get current item context. Returns (item_type, track_id, project_id, todo_id)."""
        # Determine item type based on what's set
        if self._current_todo_id is not None:
            item_type = "todo"
        elif self._current_project_id is not None:
            item_type = "project"
        elif self._current_track_id is not None:
            item_type = "track"
        else:
            item_type = "none"

        return (item_type, self._current_track_id, self._current_project_id, self._current_todo_id)


    # ========== Timer Management ==========

    def toggle_timer(self) -> None:
        """Toggle timer between IDLE/RUNNING/PAUSED states."""
        if self._timer_state == TimerStateEnum.IDLE:
            # Work time-up latch: Space is a no-op at 00:00 (user must Enter confirm or r reset).
            if self._timer_phase == TimerPhaseEnum.WORK and self._work_timeup_latched:
                return

            # Start from idle - record session start time
            self._timer_state = TimerStateEnum.RUNNING
            self._timer_start_timestamp = time.time()
            self._remaining_seconds = self._target_minutes * 60
            self._paused_remaining = None
            # Only WORK phase records session start time (BREAK is a separate timer).
            if self._timer_phase == TimerPhaseEnum.WORK:
                self._session_started_at = datetime.now(timezone.utc)  # Record for session
                self._work_warned_5min = False

        elif self._timer_state == TimerStateEnum.RUNNING:
            # Pause - calculate remaining time
            elapsed = round(time.time() - self._timer_start_timestamp) if self._timer_start_timestamp else 0
            if self._paused_remaining is not None:
                self._remaining_seconds = max(0, self._paused_remaining - elapsed)
            else:
                self._remaining_seconds = max(0, self._target_minutes * 60 - elapsed)
            self._timer_state = TimerStateEnum.PAUSED
            self._paused_remaining = self._remaining_seconds
            self._timer_start_timestamp = None

        elif self._timer_state == TimerStateEnum.PAUSED:
            # Resume from pause
            self._timer_state = TimerStateEnum.RUNNING
            self._timer_start_timestamp = time.time()
            if self._paused_remaining is not None:
                self._remaining_seconds = self._paused_remaining
        
        self._message.set(EmptyResult)

    def reset_timer(self) -> None:
        """Reset timer to IDLE state and clear session tracking."""
        # Special behavior: BREAK reset returns to WORK idle 25:00.
        if self._timer_phase == TimerPhaseEnum.BREAK:
            self._timer_phase = TimerPhaseEnum.WORK
            self._target_minutes = 25
            self._remaining_seconds = 25 * 60
        else:
            self._remaining_seconds = self._target_minutes * 60

        self._timer_state = TimerStateEnum.IDLE
        self._timer_start_timestamp = None
        self._paused_remaining = None
        self._session_started_at = None  # Clear session
        self._last_saved_session_id = None  # Clear saved session id
        self._pending_timer_event = None
        self._work_warned_5min = False
        self._work_timeup_latched = False
        self._break_armed_after_finish = False

        # Keep item context and cached data (don't clear _current_*_dict)
        # User may want to restart timer for the same item
        self._message.set(Result(True, None, "Timer reset"))

    def adjust_time(self, delta_minutes: int) -> None:
        """Adjust target time by delta minutes (only when IDLE)."""
        # Only allow adjusting WORK idle minutes (BREAK is fixed to default) and not when latched at 00:00.
        if self._timer_state == TimerStateEnum.IDLE and self._timer_phase == TimerPhaseEnum.WORK and not self._work_timeup_latched:
            new_minutes = max(5, self._target_minutes + delta_minutes)
            self._target_minutes = new_minutes
            self._remaining_seconds = new_minutes * 60

    def update_timer(self) -> bool:
        """Update timer countdown. Returns True if display should refresh."""
        if self._timer_state != TimerStateEnum.RUNNING or not self._timer_start_timestamp:
            return False

        elapsed = round(time.time() - self._timer_start_timestamp)
        old_seconds = self._remaining_seconds

        if self._paused_remaining is not None:
            self._remaining_seconds = max(0, self._paused_remaining - elapsed)
        else:
            self._remaining_seconds = max(0, self._target_minutes * 60 - elapsed)

        # Work 5-min warning: cross-threshold once (from >5:00 to <=5:00).
        if self._timer_phase == TimerPhaseEnum.WORK and not self._work_warned_5min:
            if old_seconds > 5 * 60 and self._remaining_seconds <= 5 * 60:
                self._work_warned_5min = True
                self._pending_timer_event = TimerEventEnum.WORK_5MIN_LEFT

        # Timer completed
        if self._remaining_seconds == 0:
            self._timer_state = TimerStateEnum.IDLE
            self._timer_start_timestamp = None
            self._paused_remaining = None
            if self._timer_phase == TimerPhaseEnum.WORK:
                # Latch at 00:00 for work; user can press Enter to finish or r to reset.
                self._work_timeup_latched = True
                self._pending_timer_event = TimerEventEnum.WORK_TIME_UP
            else:
                # Break ends: ring and return to WORK idle 25:00.
                self._pending_timer_event = TimerEventEnum.BREAK_TIME_UP
                self._timer_phase = TimerPhaseEnum.WORK
                self._target_minutes = 25
                self._remaining_seconds = 25 * 60
                self._work_warned_5min = False
                self._work_timeup_latched = False
            return True

        return old_seconds != self._remaining_seconds

    def consume_timer_event(self) -> TimerEventEnum | None:
        """Consume and clear the pending one-shot timer event."""
        e = self._pending_timer_event
        self._pending_timer_event = None
        return e

    def arm_break_after_finish(self, minutes: int = 5) -> None:
        """Arm break idle after the time-up finish flow completes."""
        try:
            m = int(minutes)
        except Exception:
            m = 5
        self._break_minutes_default = max(1, m)
        self._break_armed_after_finish = True

    def maybe_prepare_break_idle(self) -> bool:
        """
        If break is armed, enter BREAK idle (default 05:00) and clear session/timeup state.
        Returns True if BREAK idle was prepared.
        """
        if not self._break_armed_after_finish:
            return False

        self._break_armed_after_finish = False

        self._timer_phase = TimerPhaseEnum.BREAK
        self._timer_state = TimerStateEnum.IDLE
        self._target_minutes = int(self._break_minutes_default)
        self._remaining_seconds = self._target_minutes * 60
        self._timer_start_timestamp = None
        self._paused_remaining = None

        # Clear work-session related state.
        self._session_started_at = None
        self._last_saved_session_id = None
        self._pending_timer_event = None
        self._work_warned_5min = False
        self._work_timeup_latched = False
        return True


    # ========== Session Management ==========

    def get_session_duration_minutes(self) -> int:
        """Calculate actual session duration in minutes."""
        # Use target_minutes as base (could be improved to track actual time)
        return self._target_minutes

    def has_active_session(self) -> bool:
        """Check if there's an active session to save."""
        return self._session_started_at is not None

    def save_session(self) -> Result:
        """Save current session to database. Returns Result with session_id in data."""
        if not self._session_started_at:
            return Result(False, None, "No active session to save")

        if self._current_project_id is None and self._current_todo_id is None:
            return Result(False, None, "No project or todo selected")

        ended_at = datetime.now(timezone.utc)
        duration = self.get_session_duration_minutes()

        # Prefer todo_item_id over project_id
        if self._current_todo_id is not None:
            result = actions.save_session(
                project_id=None,
                todo_item_id=self._current_todo_id,
                duration_minutes=duration,
                started_at_utc=self._session_started_at,
                ended_at_utc=ended_at
            )
        else:
            result = actions.save_session(
                project_id=self._current_project_id,
                todo_item_id=None,
                duration_minutes=duration,
                started_at_utc=self._session_started_at,
                ended_at_utc=ended_at
            )

        if result.success:
            self._last_saved_session_id = result.data
            if self._timer_state == TimerStateEnum.RUNNING and self._timer_start_timestamp:
                self.update_timer()

            self._timer_state = TimerStateEnum.IDLE
            self._timer_start_timestamp = None
            self._paused_remaining = None
            self._session_started_at = None

        return result

    # ========== Property Getters ==========

    @property
    def current_track_id(self) -> int | None:
        return self._current_track_id

    @property
    def current_project_id(self) -> int | None:
        return self._current_project_id

    @property
    def current_todo_id(self) -> int | None:
        return self._current_todo_id

    @property
    def current_project_dict(self) -> dict | None:
        return self._current_project_dict

    @property
    def current_todo_dict(self) -> dict | None:
        return self._current_todo_dict

    @property
    def timer_state(self) -> TimerStateEnum:
        return self._timer_state

    @property
    def timer_phase(self) -> TimerPhaseEnum:
        return self._timer_phase

    @property
    def work_timeup_latched(self) -> bool:
        """Whether work timer has latched at 00:00 (time-up)."""
        return self._work_timeup_latched

    @property
    def break_armed_after_finish(self) -> bool:
        """Whether break idle is armed to start after the finish-session flow ends."""
        return self._break_armed_after_finish

    @property
    def last_saved_session_id(self) -> int | None:
        """Last persisted session id."""
        return self._last_saved_session_id

    @property
    def target_minutes(self) -> int:
        return self._target_minutes

    @property
    def remaining_seconds(self) -> int:
        return self._remaining_seconds

    @property
    def session_started_at(self) -> datetime | None:
        return self._session_started_at
