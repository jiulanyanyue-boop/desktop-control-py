from __future__ import annotations

import base64
from pathlib import Path

from PIL import Image


def test_match_window_exact_and_fuzzy() -> None:
    from desktop_control_py.backends.win32 import match_window_title

    assert match_window_title("Notepad", "Notepad", exact=True) is True
    assert match_window_title("Untitled - Notepad", "notepad", exact=False) is True
    assert match_window_title("Calculator", "notepad", exact=False) is False


def test_encode_image_payload_returns_base64_and_metadata(tmp_path: Path) -> None:
    from desktop_control_py.backends.win32 import encode_image_payload

    image = Image.new("RGB", (4, 3), color="red")

    payload = encode_image_payload(image=image, format="png", quality=90, grayscale=False)

    assert payload["mime_type"] == "image/png"
    assert payload["width"] == 4
    assert payload["height"] == 3
    assert isinstance(payload["base64_data"], str)
    assert base64.b64decode(payload["base64_data"])
