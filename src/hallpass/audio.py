"""Audio & TTS services: QSoundEffect alarm + QTextToSpeech offline."""
from __future__ import annotations

from pathlib import Path

# Lazy Qt imports to allow headless testing without PySide6
try:
    from PySide6.QtCore import QUrl
    from PySide6.QtMultimedia import QSoundEffect
    from PySide6.QtTextToSpeech import QTextToSpeech

    HAS_QT = True
except Exception:
    HAS_QT = False
    QUrl = None  # type: ignore
    QSoundEffect = None  # type: ignore
    QTextToSpeech = None  # type: ignore


class AlarmService:
    def __init__(self, sounds_dir: Path | None = None):
        self.sounds_dir = sounds_dir or Path(__file__).parent / "sounds"
        self._effect = None
        self._current = ""
        self._fallback_proc = None
        if HAS_QT:
            try:
                self._effect = QSoundEffect()
                self._effect.setLoopCount(QSoundEffect.Infinite)  # type: ignore
                self._effect.setVolume(1.0)
            except Exception:
                self._effect = None

    def list_sounds(self) -> list[str]:
        dirs = [self.sounds_dir, Path("/usr/share/hallpass/sounds")]
        out: set[str] = set()
        for d in dirs:
            if d.exists():
                for p in d.glob("*.wav"):
                    out.add(p.name)
                for p in d.glob("*.ogg"):
                    out.add(p.name)
        return sorted(out) or ["classic_chime.wav", "digital_alarm.wav", "subtle_bell.wav"]

    def _resolve(self, name: str) -> Path | None:
        for d in [self.sounds_dir, Path("/usr/share/hallpass/sounds"), Path.cwd() / "sounds"]:
            c = d / name
            if c.exists():
                return c
        return None

    def set_sound(self, name: str) -> None:
        self._current = name
        if self._effect is None or not HAS_QT:
            return
        path = self._resolve(name)
        if path:
            try:
                self._effect.setSource(QUrl.fromLocalFile(str(path)))  # type: ignore
                self._effect.setVolume(1.0)
            except Exception:
                pass

    def _fallback_play(self, path: Path, loop: bool = False) -> bool:
        import subprocess, shutil
        for cmd in [["paplay", str(path)], ["aplay", str(path)], ["ffplay", "-nodisp", "-autoexit", str(path)], ["mpg123", str(path)]]:
            if shutil.which(cmd[0]):
                try:
                    if loop:
                        self._fallback_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    continue
        return False

    def test(self) -> bool:
        name = self._current or "mixkit-facility-alarm-sound-999.wav"
        path = self._resolve(name)
        if not path:
            path = self._resolve(self._current)
        tried_qt = False
        if self._effect and HAS_QT and path and path.exists():
            try:
                self._effect.setSource(QUrl.fromLocalFile(str(path)))  # type: ignore
                self._effect.setVolume(1.0)
                self._effect.setLoopCount(1)
                self._effect.play()
                tried_qt = True
                self._effect.setLoopCount(QSoundEffect.Infinite)  # type: ignore
            except Exception:
                tried_qt = False
        if tried_qt:
            try:
                if self._effect.isPlaying():  # type: ignore
                    return True
            except Exception:
                return True
        if path and path.exists():
            if self._fallback_play(path, loop=False):
                return True
        return tried_qt

    def start(self) -> None:
        self.stop()
        path = self._resolve(self._current) if self._current else None
        if self._effect and HAS_QT and path and path.exists():
            try:
                self._effect.setSource(QUrl.fromLocalFile(str(path)))  # type: ignore
                self._effect.setVolume(1.0)
                self._effect.setLoopCount(QSoundEffect.Infinite)  # type: ignore
                self._effect.play()
                try:
                    if self._effect.isPlaying():  # type: ignore
                        return
                except Exception:
                    return
            except Exception:
                pass
        if path and path.exists():
            self._fallback_play(path, loop=True)

    def stop(self) -> None:
        if self._effect and HAS_QT:
            try:
                self._effect.stop()
            except Exception:
                pass
        if self._fallback_proc:
            try:
                self._fallback_proc.terminate()
            except Exception:
                pass
            self._fallback_proc = None


class TTSService:
    def __init__(self):
        self._tts = None
        if HAS_QT:
            try:
                self._tts = QTextToSpeech()
            except Exception:
                self._tts = None

    def speak(self, text: str) -> None:
        if not text:
            return
        if self._tts and HAS_QT:
            try:
                self._tts.say(text)
                return
            except Exception:
                pass
        # Fallback: try espeak via subprocess if Qt TTS unavailable
        try:
            import subprocess

            subprocess.Popen(["espeak-ng", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            try:
                import subprocess

                subprocess.Popen(["espeak", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def available(self) -> bool:
        return HAS_QT and self._tts is not None
