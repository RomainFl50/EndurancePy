"""Al Kamel Systems data layer.

This sub-package contains everything specific to the Al Kamel timing archives:
the HTTP client and URL building, results discovery, and the parsers that turn
the published CSV files into EndurancePy data objects.

The same parser covers WEC, ELMS, Asian Le Mans Series, Le Mans Cup and IMSA —
only the base host and minor URL details differ. See
``docs/analyse_fastf1.md`` §14 for the verified file formats and URL structure.
"""

from __future__ import annotations
