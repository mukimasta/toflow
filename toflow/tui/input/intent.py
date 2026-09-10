"""Input intents - abstract actions from key events."""

from enum import Enum


class InputIntent(str, Enum):
    FIELD_NEXT = "field_next"
    FIELD_PREV = "field_prev"
    SPACE = "space"
    SEG_NEXT = "seg_next"
    SEG_PREV = "seg_prev"
    WORD_NEXT = "word_next"
    WORD_PREV = "word_prev"
    LINE_HOME = "line_home"
    LINE_END = "line_end"
    INC = "inc"
    DEC = "dec"
    BACKSPACE = "backspace"
    CHAR = "char"
    PASTE = "paste"
