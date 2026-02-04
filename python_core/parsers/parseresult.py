"""
ParseResult: Standardized result format for all parsers.
"""
from errors import ParseError


class ParseResult:
    """Standardized result format for all parsers."""
    
    def __init__(self):
        self.events = []  # Point-in-time events
        self.states = []  # Persistent states/settings
        self.errors = []  # List of ParseError objects
        self.stats = {
            'total_records_attempted': 0,
            'records_successful': 0,
            'records_failed': 0,
            'fields_total': 0,
            'fields_extracted': 0,
            'fields_missing': 0
        }
    
    @property
    def all_rows(self):
        """Convenience property: all events and states combined."""
        return self.events + self.states
    
    def add_error(self, error):
        """Add error to result (can be ParseError or plain exception)."""
        if isinstance(error, ParseError):
            self.errors.append(error)
        else:
            # Wrap non-ParseError exceptions
            self.errors.append(ParseError(str(error), level='error'))
    
    def is_success(self):
        """True if parsing succeeded (no fatal errors). Empty results are OK."""
        has_fatal_errors = any(e.level == 'error' for e in self.errors)
        return not has_fatal_errors
    
    def to_dict(self):
        """Serialize to dict for JSON transport via Pyodide."""
        return {
            'success': self.is_success(),
            'events': self.events,
            'states': self.states,
            'errors': [e.to_dict() for e in self.errors],
            'stats': self.stats
        }
