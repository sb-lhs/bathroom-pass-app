"""Silent webcam photo audit — Surface Pro 1 UVC-optimized, Debian-ready."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from .config import photos_dir


class SilentCamera:
    """UVC-optimized for Surface Pro 1: keeps /dev/video0 open via V4L2 at 640x480 for <100ms silent snapshots.
    Front (0) faces student; rear (1) available if needed. Falls back gracefully on macOS (AVFoundation).
    """

    def __init__(self, warm: bool = True, camera_index: int = 0):
        self._warm = False
        self._cv_cap = None
        self._camera_index = camera_index  # 0 front (student-facing), 1 rear
        self._available_indices: list[int] | None = None
        if warm:
            self.warm()

    def available_indices(self, max_probe: int = 6) -> list[int]:
        # Probe /dev/video* existence first on Linux for faster, permission-aware detection
        found: list[int] = []
        try:
            import cv2  # type: ignore
            from pathlib import Path as _P
            # Prefer probing only existing /dev/video* nodes on Linux
            probe_range = range(max_probe)
            if sys.platform.startswith("linux"):
                try:
                    vdevs = sorted(_P("/dev").glob("video*"))
                    if vdevs:
                        probe_range = [int(p.name.replace("video", "")) for p in vdevs if p.name.replace("video", "").isdigit()]
                        probe_range = [i for i in probe_range if i < max_probe]
                except Exception:
                    pass
            for idx in probe_range:
                cap = None
                try:
                    if sys.platform.startswith("linux"):
                        cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
                    elif sys.platform == "darwin" and hasattr(cv2, "CAP_AVFOUNDATION"):
                        cap = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION)
                    else:
                        cap = cv2.VideoCapture(idx)
                    if cap and cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        # Try up to 3 reads to get past initial black frames
                        ok = False
                        for _ in range(3):
                            ret, frame = cap.read()
                            if ret and frame is not None and getattr(frame, "size", 0) > 0:
                                ok = True
                                break
                        if ok:
                            found.append(idx)
                        cap.release()
                    elif cap:
                        cap.release()
                except Exception:
                    try:
                        if cap:
                            cap.release()
                    except Exception:
                        pass
        except Exception:
            pass
        if not found:
            found = [self._camera_index]
        # Don't cache permanently — re-probe next time if we fell back
        if len(found) == 1 and found[0] == self._camera_index and self._available_indices is None:
            # Cache only if we actually probed devices
            self._available_indices = found
        elif found:
            self._available_indices = found
        return found

    def capture_all(self, suffix: str = "out", student: str = "", block: str = "") -> list[str]:
        paths: list[str] = []
        indices = self.available_indices()
        for idx in indices:
            cam_suffix = f"{suffix}_cam{idx}" if len(indices) > 1 else suffix
            orig_idx = self._camera_index
            self._camera_index = idx
            # Clear per-camera warm cache so each index gets fresh attempt
            p = self.capture(cam_suffix, student, block)
            self._camera_index = orig_idx
            if p:
                paths.append(p)
        return paths

    def warm(self) -> None:
        """Keep stream open in background as tip recommends — no per-shot init lag."""
        try:
            photos_dir().mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            import cv2  # type: ignore
            # Surface Pro 1 Debian: V4L2 is the native UVC backend (uvcvideo module)
            # macOS: AVFoundation. Keep one continuously open cap for instant read().
            cap = None
            if sys.platform.startswith("linux"):
                cap = cv2.VideoCapture(self._camera_index, cv2.CAP_V4L2)
            elif sys.platform == "darwin" and hasattr(cv2, "CAP_AVFOUNDATION"):
                cap = cv2.VideoCapture(self._camera_index, cv2.CAP_AVFOUNDATION)
                if not cap.isOpened():
                    cap.release()
                    cap = cv2.VideoCapture(self._camera_index)
            else:
                cap = cv2.VideoCapture(self._camera_index)
            if cap and cap.isOpened():
                # Low resolution for fast <100ms capture as per tip
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                # One warm read to trigger uvcvideo / permission and fill buffer
                cap.read()
                self._cv_cap = cap
                self._warm = True
            else:
                if cap:
                    cap.release()
                # Try front if rear failed, vice versa
                alt = 1 if self._camera_index == 0 else 0
                cap2 = cv2.VideoCapture(alt, cv2.CAP_V4L2) if sys.platform.startswith("linux") else cv2.VideoCapture(alt)
                if cap2 and cap2.isOpened():
                    cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap2.read()
                    self._cv_cap = cap2
                    self._warm = True
                elif cap2:
                    cap2.release()
        except Exception:
            pass

    def _quick_opencv_capture(self, target: Path) -> bool:
        """Single fast read from the kept-open stream — no 0.5s sleeps, no multi-index loops."""
        try:
            import cv2  # type: ignore
            cap = self._cv_cap
            # Use kept-open stream first (instant)
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and getattr(frame, "size", 0) > 0:
                    cv2.imwrite(str(target), frame)
                    if target.exists() and target.stat().st_size > 1000:
                        return True
            # Fallback: one fresh open on the same index (V4L2 front) — still <200ms
            fresh = None
            if sys.platform.startswith("linux"):
                fresh = cv2.VideoCapture(self._camera_index, cv2.CAP_V4L2)
            else:
                fresh = cv2.VideoCapture(self._camera_index)
            if fresh and fresh.isOpened():
                fresh.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                fresh.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                ret, frame = fresh.read()
                fresh.release()
                if ret and frame is not None and getattr(frame, "size", 0) > 0:
                    cv2.imwrite(str(target), frame)
                    if target.exists() and target.stat().st_size > 1000:
                        # Re-warm for next shot
                        try:
                            nc = cv2.VideoCapture(self._camera_index, cv2.CAP_V4L2) if sys.platform.startswith("linux") else cv2.VideoCapture(self._camera_index)
                            if nc and nc.isOpened():
                                nc.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                                nc.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                                nc.read()
                                if self._cv_cap:
                                    try:
                                        self._cv_cap.release()
                                    except Exception:
                                        pass
                                self._cv_cap = nc
                                self._warm = True
                            elif nc:
                                nc.release()
                        except Exception:
                            pass
                        return True
            elif fresh:
                fresh.release()
        except Exception:
            pass
        return False

    def capture(self, suffix: str = "out", student: str = "", block: str = "") -> str:
        """Fast silent capture. Filename is name + timestamp, linked to pass event. Returns path."""
        dt = datetime.now()
        ts = dt.strftime("%Y%m%d_%H%M%S")
        datestr = dt.strftime("%Y-%m-%d_%H-%M-%S")

        def clean(s: str) -> str:
            s = (s or "").strip().replace(" ", "_")
            import re
            s = re.sub(r"[^A-Za-z0-9_\-]", "", s)
            return s[:32] or "Unknown"

        s_clean = clean(student)
        b_clean = clean(block)
        if s_clean != "Unknown" or b_clean != "Unknown":
            fname = f"{datestr}_{s_clean}_{b_clean}_{suffix}.jpg"
        else:
            fname = f"{datestr}_{suffix}.jpg"
        p = photos_dir() / fname
        counter = 0
        while p.exists():
            counter += 1
            p = photos_dir() / f"{ts}_{suffix}_{counter}.jpg"
        try:
            photos_dir().mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        if self._quick_opencv_capture(p):
            return str(p)

        # Fallback: instructional placeholder (Surface Pro 1 tip: check lsusb/v4l2-ctl/modprobe/video group)
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
            img = np.full((480, 640, 3), 242, dtype=np.uint8)
            cv2.putText(img, "NO CAMERA", (18, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (20, 20, 20), 2)
            cv2.putText(img, f"{ts} {suffix}", (18, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 60), 1)
            if sys.platform.startswith("linux"):
                cv2.putText(img, "Debian: sudo usermod -aG video $USER", (18, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (30, 30, 30), 1)
                cv2.putText(img, "then lsusb & v4l2-ctl --list-devices", (18, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (30, 30, 30), 1)
                cv2.putText(img, "sudo modprobe uvcvideo", (18, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (30, 30, 30), 1)
            else:
                cv2.putText(img, "Grant camera access:", (18, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 1)
                cv2.putText(img, "System Settings > Privacy & Security", (18, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1)
                cv2.putText(img, "> Camera > Allow Terminal", (18, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1)
            cv2.putText(img, "Then relaunch hallpass", (18, 345), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1)
            cv2.imwrite(str(p), img)
            return str(p)
        except Exception:
            pass
        try:
            p.write_bytes(b"")
        except Exception:
            pass
        return str(p)

    def release(self) -> None:
        if self._cv_cap is not None:
            try:
                self._cv_cap.release()
            except Exception:
                pass
            self._cv_cap = None
