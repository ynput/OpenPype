"""Fake 'charset_normalizer' for Python 2 to raise ImportError.

Needed for 'requests' module which first checks for existence of
'charset_normalizer' (Python 3) but does not raise 'ImportError' but
'SyntaxError'.
"""

raise ImportError("charset_normalizer not available")
