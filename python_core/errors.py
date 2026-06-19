"""
Error hierarchy for standardized error reporting across parsers.

Errors are categorized by severity level:
- error: File/data cannot be parsed at all (fatal)
- warning: Some records/fields failed but parsing continued (partial success)
- info: Non-critical information (field missing but has default)
"""


class ParseError(Exception):
    """Base parsing error with severity level and context."""

    def __init__(self, msg: str, level: str = "error", context: dict = None):
        """Level is 'error' | 'warning' | 'info'; context carries filename/row_idx/field_name."""
        super().__init__(msg)
        self.msg = msg
        self.level = level
        self.context: dict = context or {}

    def to_dict(self) -> dict:
        """Serialize to dict for JSON transport."""
        return {"level": self.level, "msg": self.msg, "context": self.context}


class FileLevelError(ParseError):
    """File cannot be parsed - entire file is unusable. FATAL."""

    def __init__(self, msg: str, context: dict = None):
        super().__init__(msg, level="error", context=context)


class RecordLevelError(ParseError):
    """Record/row in file failed, but other records succeeded. WARNING."""

    def __init__(self, msg: str, context: dict = None):
        super().__init__(msg, level="warning", context=context)


class FieldLevelError(ParseError):
    """Field extraction failed but record is still usable. INFO."""

    def __init__(self, msg: str, context: dict = None):
        super().__init__(msg, level="info", context=context)
