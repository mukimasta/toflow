"""
Renderer & Layout constants (tunable parameters).

Design:
- Pure constants only (no runtime logic).
- Names are explicit and readable.
- Defaults are conservative: keep UI stable and predictable.
"""

# =============================================================================
# Viewport (implicit scrolling)
# =============================================================================

# For line-based lists: keep this many lines as a safety margin around the cursor.
VIEWPORT_CURSOR_MARGIN_LINES = 1


# =============================================================================
# Renderer sizing
# =============================================================================

# TrackWithProjects (Structure) box width in characters.
STRUCTURE_TWP_BOX_WIDTH = 60

# Generic separator line display width (used where a fixed-length separator is rendered).
SEPARATOR_LINE_WIDTH = 70

# NOW view box width (ASCII box).
NOW_VIEW_BOX_WIDTH = 50


# =============================================================================
# Blocks (list rendering)
# =============================================================================

# For list views, clamp the effective terminal width so alignment doesn't collapse on narrow windows.
LIST_MIN_TERMINAL_WIDTH = 40

# For list views, clamp the content width so structure line formatting always has enough space.
LIST_MIN_CONTENT_WIDTH = 20

# Timeline: preview this many chars of session description.
TIMELINE_TAKEAWAY_PREVIEW_CHARS = 30


# =============================================================================
# LayoutManager sizing
# =============================================================================

# NOW View layout
NOW_BOX_WIDTH = NOW_VIEW_BOX_WIDTH
NOW_PADDING_LEFT_RIGHT_WEIGHT = 6
NOW_PADDING_TOP_WEIGHT = 50
NOW_PADDING_BOTTOM_WEIGHT = 55

# Input Mode form panel widths (fixed)
INPUT_PURPOSE_WIDTH = 16
INPUT_TITLE_WIDTH = 30
INPUT_DATE_WIDTH = 15
INPUT_CONTENT_WIDTH = 52


