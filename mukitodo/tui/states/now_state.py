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

        # == Session Tracking ==
        self._session_started_at: datetime | None = None  # For database persistence
        self._last_saved_session_id: int | None = None  # For linking takeaways


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
            # Start from idle - record session start time
            self._timer_state = TimerStateEnum.RUNNING
            self._timer_start_timestamp = time.time()
            self._remaining_seconds = self._target_minutes * 60
            self._paused_remaining = None
            self._session_started_at = datetime.now(timezone.utc)  # Record for session

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

    def reset_timer(self) -> None:
        """Reset timer to IDLE state and clear session tracking."""
        self._timer_state = TimerStateEnum.IDLE
        self._remaining_seconds = self._target_minutes * 60
        self._timer_start_timestamp = None
        self._paused_remaining = None
        self._session_started_at = None  # Clear session
        self._last_saved_session_id = None  # Clear saved session id

        # Keep item context and cached data (don't clear _current_*_dict)
        # User may want to restart timer for the same item

    def adjust_time(self, delta_minutes: int) -> None:
        """Adjust target time by delta minutes (only when IDLE)."""
        if self._timer_state == TimerStateEnum.IDLE:
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

        # Timer completed
        if self._remaining_seconds == 0:
            self._timer_state = TimerStateEnum.IDLE
            self._timer_start_timestamp = None
            self._paused_remaining = None
            return True

        return old_seconds != self._remaining_seconds


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

    def create_takeaway_for_session(self, content: str) -> Result:
        """Create a takeaway linked to the last saved session."""
        from datetime import date as date_type

        if self._last_saved_session_id is None:
            return Result(False, None, "No session to link takeaway to")

        # Use todo_item_id or project_id as parent
        result = actions.create_takeaway(
            title=None,
            content=content,
            type="action",
            date=date_type.today(),
            project_id=self._current_project_id if self._current_todo_id is None else None,
            todo_item_id=self._current_todo_id,
            now_session_id=self._last_saved_session_id
        )

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
    def last_saved_session_id(self) -> int | None:
        """Last persisted session id (used for linking takeaways)."""
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
