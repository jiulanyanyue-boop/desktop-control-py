"""管理 Computer Use 风格观察截图的本地 artifact。"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .errors import DesktopControlError


@dataclass(frozen=True, slots=True)
class ScreenshotArtifact:
    """表示一次截图落盘后的可引用元数据。"""

    id: str
    path: str
    mime_type: str
    width: int
    height: int

    def to_dict(self) -> dict[str, int | str]:
        """转换为 MCP 结构化输出可直接序列化的字典。"""

        return {
            "id": self.id,
            "path": self.path,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
        }


class ScreenshotArtifactStore:
    """负责把 base64 截图载荷保存为 runtime 下的可审计文件。"""

    def __init__(self, artifact_dir: Path) -> None:
        """保存 artifact 目录，并确保目录存在。"""

        self._artifact_dir = artifact_dir
        self._artifact_dir.mkdir(parents=True, exist_ok=True)

    def save(self, screenshot: dict, label: str = "observe") -> ScreenshotArtifact:
        """保存截图载荷，并返回可序列化的 artifact 元数据。"""

        safe_label = self._normalize_label(label)
        mime_type = str(screenshot.get("mime_type") or "image/png")
        extension = self._extension_for_mime_type(mime_type)
        artifact_id = self._new_artifact_id(safe_label)
        artifact_path = self._artifact_dir / f"{artifact_id}.{extension}"

        base64_data = screenshot.get("base64_data")
        if not isinstance(base64_data, str) or not base64_data:
            raise DesktopControlError(
                code="invalid_screenshot_payload",
                message="Screenshot payload does not contain base64 image data.",
            )

        try:
            image_bytes = base64.b64decode(base64_data, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise DesktopControlError(
                code="invalid_screenshot_payload",
                message="Screenshot payload contains invalid base64 image data.",
            ) from exc

        artifact_path.write_bytes(image_bytes)
        return ScreenshotArtifact(
            id=artifact_id,
            path=str(artifact_path),
            mime_type=mime_type,
            width=int(screenshot.get("width") or 0),
            height=int(screenshot.get("height") or 0),
        )

    @staticmethod
    def _normalize_label(label: str) -> str:
        """把调用方标签规范化为适合文件名的短标识。"""

        normalized = "".join(char.lower() if char.isalnum() else "-" for char in label.strip())
        return normalized.strip("-") or "observe"

    @staticmethod
    def _extension_for_mime_type(mime_type: str) -> str:
        """根据 MIME 类型选择稳定文件扩展名。"""

        if mime_type == "image/jpeg":
            return "jpg"
        return "png"

    @staticmethod
    def _new_artifact_id(label: str) -> str:
        """生成按时间排序且避免冲突的 artifact 标识。"""

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        return f"{timestamp}-{label}-{uuid4().hex[:8]}"
