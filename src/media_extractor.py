"""Best-effort media signal extraction with timeout/retry and graceful fallback."""

from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None


logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
GENERIC_FILENAME_TOKENS = {"img", "image", "vid", "video", "dsc", "pxl", "mvimg"}


class MediaExtractor:
    def __init__(self, timeout_seconds=8, max_retries=2, backoff_seconds=0.4):
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.max_retries = max(0, int(max_retries))
        self.backoff_seconds = max(0.0, float(backoff_seconds))

    def _normalize(self, value, max_len=1200):
        compact = " ".join(str(value or "").split()).strip()
        return compact[:max_len]

    def _filename_hint(self, media_path: Path, max_words=8):
        stem = media_path.stem.replace("_", " ").replace("-", " ")
        tokens = re.findall(r"[A-Za-z0-9]+", stem)
        tokens = [t for t in tokens if not t.isdigit() and t.lower() not in GENERIC_FILENAME_TOKENS]
        return " ".join(tokens[:max_words])

    def _run_with_timeout_retry(self, label, func):
        last_error = None
        for attempt in range(self.max_retries + 1):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(func)
                try:
                    return future.result(timeout=self.timeout_seconds)
                except FutureTimeoutError as err:
                    last_error = err
                    logger.warning("%s timed out on attempt %s", label, attempt + 1)
                except Exception as err:  # pragma: no cover - defensive
                    last_error = err
                    logger.warning("%s failed on attempt %s: %s", label, attempt + 1, err)
            if attempt < self.max_retries and self.backoff_seconds > 0:
                time.sleep(self.backoff_seconds * (attempt + 1))
        if last_error:
            logger.warning("%s exhausted retries: %s", label, last_error)
        return ""

    def _extract_ocr(self, media_path: Path, is_video: bool):
        if pytesseract is None or Image is None:
            return ""
        if is_video:
            if cv2 is None:
                return ""
            cap = cv2.VideoCapture(str(media_path))
            try:
                ok, frame = cap.read()
                if not ok or frame is None:
                    return ""
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                text = pytesseract.image_to_string(rgb)
                return self._normalize(text, max_len=600)
            finally:
                cap.release()
        with Image.open(media_path) as img:
            text = pytesseract.image_to_string(img)
            return self._normalize(text, max_len=600)

    def _extract_audio_transcript(self, media_path: Path, is_video: bool):
        # Optional STT dependencies are not required for runtime stability.
        # Graceful fallback returns an empty transcript if unavailable.
        _ = media_path
        _ = is_video
        return ""

    def _extract_keyframe_summary(self, media_path: Path, is_video: bool):
        filename_hint = self._filename_hint(media_path)
        if is_video and cv2 is not None:
            cap = cv2.VideoCapture(str(media_path))
            try:
                if not cap.isOpened():
                    return self._normalize(filename_hint)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
                frame_count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
                duration = (frame_count / fps) if fps > 0 else 0.0
                parts = []
                if filename_hint:
                    parts.append(filename_hint)
                if width and height:
                    parts.append(f"{width}x{height} video")
                if duration > 0:
                    parts.append(f"~{duration:.1f}s")
                return self._normalize(", ".join(parts), max_len=240)
            finally:
                cap.release()
        if not is_video and Image is not None:
            try:
                with Image.open(media_path) as img:
                    width, height = img.size
                    mode = str(getattr(img, "mode", "") or "").strip()
                    parts = []
                    if filename_hint:
                        parts.append(filename_hint)
                    if width and height:
                        parts.append(f"{width}x{height} image")
                    if mode:
                        parts.append(mode)
                    return self._normalize(", ".join(parts), max_len=240)
            except Exception:  # pragma: no cover - defensive
                pass
        return self._normalize(filename_hint, max_len=240)

    def extract_media_signals(self, media_path: Path):
        path = Path(media_path)
        extension = path.suffix.lower().lstrip(".")
        is_video = extension in VIDEO_EXTENSIONS
        return {
            "ocr_text": self._run_with_timeout_retry(
                f"ocr:{path.name}",
                lambda: self._extract_ocr(path, is_video)
            ),
            "transcript_text": self._run_with_timeout_retry(
                f"transcript:{path.name}",
                lambda: self._extract_audio_transcript(path, is_video)
            ),
            "keyframe_summary": self._run_with_timeout_retry(
                f"keyframes:{path.name}",
                lambda: self._extract_keyframe_summary(path, is_video)
            ),
        }
