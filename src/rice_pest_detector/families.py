"""Map Roboflow export filenames to their source-image family."""

import re

_ROBOFLOW = re.compile(
    r"^(?P<stem>.+?)_(?:jpe?g|png)\.rf\.[0-9a-f]+\.(?:jpe?g|png)$",
    re.IGNORECASE,
)


def family_key(filename: str) -> str:
    """Return the lower-cased source stem shared by every export variant of one photo."""
    match = _ROBOFLOW.match(filename)
    if match is None:
        raise ValueError(f"not a Roboflow export filename: {filename!r}")
    return match.group("stem").lower()
