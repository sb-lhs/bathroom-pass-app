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
        # Also check /usr/share/hallpass/sounds for deployed
        self._effect = None
        self._current = ""
        if HAS_QT:
            try:
                self._effect = QSoundEffect()
                self._effect.setLoopCount(QSoundEffect.Infinite)  # type: ignore
                self._effect.setVolume(0.9)
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
            except Exception:
                pass

    def test(self) -> None:
        if self._effect and HAS_QT:
            try:
                self._effect.setLoopCount(1)
                self._effect.play()
                self._effect.setLoopCount(QSoundEffect.Infinite)  # type: ignore
            except Exception:
                pass

    def start(self) -> None:
        if self._effect and HAS_QT:
            try:
                self._effect.play()
            except Exception:
                pass

    def stop(self) -> None:
        if self._effect and HAS_QT:
            try:
                self._effect.stop()
            except Exception:
                pass


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
