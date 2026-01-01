from datetime import date as date_type
from mukitodo import actions
from mukitodo.actions import Result, EmptyResult
from mukitodo.tui.states.message_holder import MessageHolder


class TimelineState:
    """State management for Timeline View."""

    def __init__(self, message_holder: MessageHolder):
        self._message = message_holder

        # Raw data from actions.list_timeline_records()
        # list[(session_dict | None, [takeaway_dict, ...])]
        self._records_list: list[tuple[dict | None, list[dict]]] = []

        # Flattened rows for cursor navigation and rendering
        # row_type: "date_header" | "session" | "takeaway" | "standalone_takeaway"
        # Each row structure:
        #   date_header: (row_type, date_str)
        #   session: (row_type, session_dict, session_num, takeaway_count)
        #   takeaway: (row_type, takeaway_dict, takeaway_num, is_last, parent_session_dict)
        #   standalone_takeaway: (row_type, takeaway_dict)
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

        self._records_list = result.data or []
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

        # Group records by date
        date_groups: dict[date_type, list[tuple[dict | None, list[dict]]]] = {}

        for session_dict, takeaway_dicts in self._records_list:
            # Determine the date for this record
            if session_dict:
                # Use session's ended_at_utc date
                ended_at = session_dict.get("ended_at_utc")
                if ended_at:
                    record_date = ended_at.date()
                else:
                    record_date = date_type.today()
            else:
                # Standalone takeaway - use first takeaway's created_at_utc
                if takeaway_dicts:
                    created_at = takeaway_dicts[0].get("created_at_utc")
                    if created_at:
                        record_date = created_at.date()
                    else:
                        record_date = date_type.today()
                else:
                    continue  # Skip empty records

            if record_date not in date_groups:
                date_groups[record_date] = []
            date_groups[record_date].append((session_dict, takeaway_dicts))

        # Sort dates descending
        sorted_dates = sorted(date_groups.keys(), reverse=True)

        session_counter = 0
        for record_date in sorted_dates:
            # Add date header
            date_str = record_date.strftime("%Y-%m-%d")
            self._flat_rows.append(("date_header", date_str))

            # Add records for this date
            for session_dict, takeaway_dicts in date_groups[record_date]:
                if session_dict:
                    # Session row
                    session_counter += 1
                    takeaway_count = len(takeaway_dicts)
                    self._flat_rows.append(("session", session_dict, session_counter, takeaway_count))

                    # Takeaway rows under this session
                    for i, takeaway_dict in enumerate(takeaway_dicts):
                        is_last = (i == len(takeaway_dicts) - 1)
                        self._flat_rows.append(("takeaway", takeaway_dict, i + 1, is_last, session_dict))
                else:
                    # Standalone takeaway
                    for takeaway_dict in takeaway_dicts:
                        self._flat_rows.append(("standalone_takeaway", takeaway_dict))

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

    def is_selected_takeaway(self) -> bool:
        """Check if current selection is a Takeaway row (linked or standalone)."""
        row = self.get_selected_row()
        return row is not None and row[0] in ("takeaway", "standalone_takeaway")

    def get_parent_session_for_selected(self) -> dict | None:
        """Get the parent session for the current selection (if any)."""
        row = self.get_selected_row()
        if row is None:
            return None

        if row[0] == "session":
            return row[1]  # session_dict
        elif row[0] == "takeaway":
            return row[4]  # parent_session_dict
        return None

    def get_selected_item_id(self) -> tuple[str, int] | None:
        """Return (item_type, item_id) for the selected row."""
        row = self.get_selected_row()
        if row is None:
            return None

        if row[0] == "session":
            session_dict = row[1]
            return ("session", session_dict["id"])
        elif row[0] == "takeaway":
            takeaway_dict = row[1]
            return ("takeaway", takeaway_dict["id"])
        elif row[0] == "standalone_takeaway":
            takeaway_dict = row[1]
            return ("takeaway", takeaway_dict["id"])
        return None

    def get_selected_takeaway_content(self) -> tuple[str, str] | None:
        """Return (title, content) for editing the selected takeaway."""
        row = self.get_selected_row()
        if row is None:
            return None

        if row[0] in ("takeaway", "standalone_takeaway"):
            takeaway_dict = row[1]
            return (takeaway_dict.get("title", ""), takeaway_dict.get("content", ""))
        return None

    # === Actions ===

    def delete_selected_item(self) -> Result:
        """Delete the currently selected Session or Takeaway."""
        item_info = self.get_selected_item_id()
        if item_info is None:
            return Result(False, None, "No item selected")

        item_type, item_id = item_info

        if item_type == "session":
            result = actions.delete_session(item_id)
        else:  # takeaway
            result = actions.delete_takeaway(item_id)

        if result.success:
            self.load_timeline_data()

        self._message.set(result)
        return result

    def create_takeaway_for_session(self, title: str, content: str, takeaway_type: str = "action") -> Result:
        """Create a new takeaway linked to the parent session of current selection."""
        parent_session = self.get_parent_session_for_selected()
        if parent_session is None:
            return Result(False, None, "No session to link takeaway to")

        # Get the session's project_id or todo_item_id to inherit
        project_id = parent_session.get("project_id")
        todo_item_id = parent_session.get("todo_item_id")
        now_session_id = parent_session.get("id")

        # Determine which parent to use (prefer todo_item_id, then project_id)
        if todo_item_id is not None:
            result = actions.create_takeaway(
                title=title or None,
                content=content,
                type=takeaway_type,
                date=date_type.today(),
                todo_item_id=todo_item_id,
                now_session_id=now_session_id
            )
        elif project_id is not None:
            result = actions.create_takeaway(
                title=title or None,
                content=content,
                type=takeaway_type,
                date=date_type.today(),
                project_id=project_id,
                now_session_id=now_session_id
            )
        else:
            return Result(False, None, "Session has no project or todo reference")

        if result.success:
            self.load_timeline_data()

        self._message.set(result)
        return result

    def update_selected_takeaway(self, title: str, content: str) -> Result:
        """Update the title and content of the selected takeaway."""
        item_info = self.get_selected_item_id()
        if item_info is None or item_info[0] != "takeaway":
            return Result(False, None, "No takeaway selected")

        takeaway_id = item_info[1]

        # Update title
        if title:
            result = actions.update_takeaway_title(takeaway_id, title)
            if not result.success:
                self._message.set(result)
                return result

        # Update content
        result = actions.update_takeaway_content(takeaway_id, content)
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
