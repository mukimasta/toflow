from datetime import date as date_type, datetime
from mukitodo import actions
from mukitodo.actions import Result, EmptyResult
from mukitodo.tui.states.message_holder import MessageHolder


class TimelineState:
    """State management for Timeline View."""

    def __init__(self, message_holder: MessageHolder):
        self._message = message_holder

        # Raw data from actions.list_timeline_records()
        # list[session_dict]
        self._sessions_list: list[dict] = []

        # Flattened rows for cursor navigation and rendering
        # row_type: "date_header" | "session"
        # Each row structure:
        #   date_header: (row_type, date_str)
        #   session: (row_type, session_dict, session_num)
        self._flat_rows: list[tuple] = []

        # Selected row index (None if no selectable rows)
        self._selected_row_idx: int | None = None

        # Initialize
        self.load_timeline_data()

    # === Data Loading ===

    def load_timeline_data(self) -> None:
        """Load timeline data from database and build flat rows for rendering."""
        result = actions.list_timeline_records()
        if not result.success:
            self._message.set(result)
            return

        self._sessions_list = result.data or []
        self._build_flat_rows()

        # Reset selection if needed
        selectable_rows = [i for i, row in enumerate(self._flat_rows) if row[0] != "date_header"]
        if selectable_rows:
            if self._selected_row_idx is None or self._selected_row_idx not in selectable_rows:
                self._selected_row_idx = selectable_rows[0] if selectable_rows else None
        else:
            self._selected_row_idx = None

    def _build_flat_rows(self) -> None:
        """Build flattened row list from records, grouped by date."""
        self._flat_rows = []

        def _local_date(dt: datetime) -> date_type:
            return dt.astimezone().date()

        # Group sessions by date
        date_groups: dict[date_type, list[dict]] = {}
        for session_dict in self._sessions_list:
            ended_at = session_dict.get("ended_at_utc")
            record_date = _local_date(ended_at) if ended_at else date_type.today()
            if record_date not in date_groups:
                date_groups[record_date] = []
            date_groups[record_date].append(session_dict)

        # Sort dates descending
        sorted_dates = sorted(date_groups.keys(), reverse=True)

        session_counter = 0
        for record_date in sorted_dates:
            # Add date header
            date_str = record_date.strftime("%Y-%m-%d")
            self._flat_rows.append(("date_header", date_str))

            # Add sessions for this date
            for session_dict in date_groups[record_date]:
                session_counter += 1
                self._flat_rows.append(("session", session_dict, session_counter))

    # === Navigation ===

    def move_cursor(self, delta: int) -> None:
        """Move cursor by delta, skipping date_header rows."""
        if self._selected_row_idx is None:
            return

        selectable_indices = [i for i, row in enumerate(self._flat_rows) if row[0] != "date_header"]
        if not selectable_indices:
            return

        # Find current position in selectable list
        try:
            current_pos = selectable_indices.index(self._selected_row_idx)
        except ValueError:
            current_pos = 0

        # Calculate new position
        new_pos = max(0, min(len(selectable_indices) - 1, current_pos + delta))
        self._selected_row_idx = selectable_indices[new_pos]
        self._message.set(EmptyResult)

    # === Getters ===

    def get_selected_row(self) -> tuple | None:
        """Return the currently selected row tuple."""
        if self._selected_row_idx is None or self._selected_row_idx >= len(self._flat_rows):
            return None
        return self._flat_rows[self._selected_row_idx]

    def is_selected_session(self) -> bool:
        """Check if current selection is a Session row."""
        row = self.get_selected_row()
        return row is not None and row[0] == "session"

    def get_parent_session_for_selected(self) -> dict | None:
        """Get the parent session for the current selection (if any)."""
        row = self.get_selected_row()
        if row is None:
            return None

        if row[0] == "session":
            return row[1]  # session_dict
        return None

    def get_selected_item_id(self) -> tuple[str, int] | None:
        """Return (item_type, item_id) for the selected row."""
        row = self.get_selected_row()
        if row is None:
            return None

        if row[0] == "session":
            session_dict = row[1]
            return ("session", session_dict["id"])
        return None

    # === Actions ===

    def delete_selected_item(self) -> Result:
        """Delete the currently selected Session."""
        item_info = self.get_selected_item_id()
        if item_info is None:
            return Result(False, None, "No item selected")

        item_type, item_id = item_info

        if item_type != "session":
            return Result(False, None, "No session selected")

        result = actions.delete_session(item_id)

        if result.success:
            self.load_timeline_data()

        self._message.set(result)
        return result

    # === Properties ===

    @property
    def flat_rows(self) -> list[tuple]:
        """Return the flattened rows list."""
        return self._flat_rows

    @property
    def selected_row_idx(self) -> int | None:
        """Return the selected row index."""
        return self._selected_row_idx

    @property
    def has_data(self) -> bool:
        """Check if there's any timeline data."""
        return len(self._flat_rows) > 0
