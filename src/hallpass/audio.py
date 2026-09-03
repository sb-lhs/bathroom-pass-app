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
    def __init__(self, voices_dir: Path | None = None):
        self._tts = None
        self._piper_voice = None
        self._piper_model = None
        # Try bundled Piper first (natural voice, offline)
        try:
            candidates = [
                (voices_dir or Path(__file__).parent / "voices" / "en_US-lessac-medium.onnx"),
                Path("/usr/share/hallpass/voices/en_US-lessac-medium.onnx"),
                Path.cwd() / "voices" / "en_US-lessac-medium.onnx",
                Path.cwd() / "src" / "hallpass" / "voices" / "en_US-lessac-medium.onnx",
            ]
            for mp in candidates:
                if mp.exists() and (mp.with_suffix(".onnx.json").exists() or Path(str(mp) + ".json").exists()):
                    try:
                        from piper import PiperVoice  # type: ignore

                        self._piper_voice = PiperVoice.load(str(mp))
                        self._piper_model = mp
                        break
                    except Exception:
                        continue
        except Exception:
            self._piper_voice = None
        # Qt TTS as second fallback
        if HAS_QT:
            try:
                self._tts = QTextToSpeech()
                # Force English voice if available to avoid zh accent
                try:
                    for v in self._tts.availableVoices():
                        name = getattr(v, "name", lambda: "")() if callable(getattr(v, "name", None)) else str(v)
                        lang = getattr(v, "language", lambda: "")() if callable(getattr(v, "language", None)) else ""
                        if "en" in str(name).lower() or "en" in str(lang).lower() or "english" in str(name).lower():
                            self._tts.setVoice(v)
                            break
                except Exception:
                    pass
            except Exception:
                self._tts = None

    def speak(self, text: str) -> None:
        if not text:
            return
        # 1) Piper (bundled natural voice)
        if self._piper_voice is not None:
            try:
                import tempfile, subprocess, shutil, wave

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    wav_path = tf.name
                try:
                    # Piper synthesize
                    with wave.open(wav_path, "wb") as wav_file:
                        self._piper_voice.synthesize(text, wav_file)
                    # Play via paplay/aplay
                    for cmd in ["paplay", "aplay"]:
                        if shutil.which(cmd):
                            subprocess.Popen([cmd, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            return
                    # Fallback ffplay
                    if shutil.which("ffplay"):
                        subprocess.Popen(["ffplay", "-nodisp", "-autoexit", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return
                finally:
                    # Cleanup after short delay — let player open file
                    try:
                        import threading

                        def _unlink(p=wav_path):
                            import time, pathlib

                            time.sleep(3)
                            try:
                                pathlib.Path(p).unlink(missing_ok=True)
                            except Exception:
                                pass

                        threading.Thread(target=_unlink, daemon=True).start()
                    except Exception:
                        pass
                return
            except Exception:
                pass
        # 2) Qt TTS with English voice forced
        if self._tts and HAS_QT:
            try:
                self._tts.say(text)
                return
            except Exception:
                pass
        # 3) espeak-ng with explicit en-us (not bare en) to fix accent
        try:
            import subprocess, shutil

            if shutil.which("espeak-ng"):
                subprocess.Popen(["espeak-ng", "-v", "en-us", "-s", "150", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            if shutil.which("espeak"):
                subprocess.Popen(["espeak", "-v", "en-us", "-s", "150", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
        except Exception:
            pass

    def available(self) -> bool:
        return self._piper_voice is not None or (HAS_QT and self._tts is not None)
