from __future__ import annotations

import asyncio
import tempfile
import threading
from pathlib import Path


class SpeechEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pygame_ready = False

    def listen_once(self, language: str = "bn-BD") -> str:
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise RuntimeError("SpeechRecognition is not installed. Run install.bat again.") from exc
        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 0.8
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.45)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=12)
            return recognizer.recognize_google(audio, language=language)
        except sr.WaitTimeoutError as exc:
            raise RuntimeError("I did not hear anything. Try speaking closer to the microphone.") from exc
        except sr.UnknownValueError as exc:
            raise RuntimeError("I could not understand that speech. Please try again.") from exc
        except sr.RequestError as exc:
            raise RuntimeError("Speech recognition needs an internet connection. Check your connection and retry.") from exc
        except OSError as exc:
            raise RuntimeError("No usable microphone found. Check Windows microphone permissions and input device.") from exc

    def speak(self, text: str, voice: str = "bn-BD-PradeepNeural") -> None:
        if not text.strip():
            return
        with self._lock:
            try:
                asyncio.run(self._edge_speak(text[:3000], voice))
                return
            except Exception:
                pass
            self._speak_fallback(text[:1000])

    async def _edge_speak(self, text: str, voice: str) -> None:
        import edge_tts
        import pygame
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out = Path(f.name)
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%", volume="+0%")
            await communicate.save(str(out))
            if not self._pygame_ready:
                pygame.mixer.init()
                self._pygame_ready = True
            pygame.mixer.music.load(str(out))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.12)
            pygame.mixer.music.unload()
        finally:
            try:
                out.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _speak_fallback(text: str) -> None:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception:
            return
