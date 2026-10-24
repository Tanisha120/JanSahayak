"""
JanSahayak Speech Service
Handles speech-to-text (transcription) and text-to-speech (spoken voice responses)
in both Hindi and English with local caching, single-retry resilience,
and graceful fallback to text input.
"""

import os
import io
import hashlib
import threading
import time
from collections import OrderedDict
from typing import Optional, Tuple, Dict, Any
import speech_recognition as sr
from gtts import gTTS

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


class SpeechService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Adjust energy threshold and silence duration for better speech detection
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        # In-memory LRU cache {cache_key: mp3 bytes}: avoids disk I/O and repeat gTTS calls
        # on every Streamlit rerun. Guarded by a lock because sessions run on separate threads.
        self._mem_cache: "OrderedDict[str, bytes]" = OrderedDict()
        self._mem_cache_max = 64
        self._mem_cache_lock = threading.Lock()

    def _mem_cache_get(self, key: str) -> Optional[bytes]:
        with self._mem_cache_lock:
            data = self._mem_cache.get(key)
            if data is not None:
                self._mem_cache.move_to_end(key)  # mark as most recently used
            return data

    def _mem_cache_put(self, key: str, data: bytes) -> None:
        with self._mem_cache_lock:
            self._mem_cache[key] = data
            self._mem_cache.move_to_end(key)
            while len(self._mem_cache) > self._mem_cache_max:
                self._mem_cache.popitem(last=False)  # evict least recently used

    def synthesize_speech(self, text: str, language: str = "hi") -> Optional[bytes]:
        """
        Synthesizes spoken audio for given text in Hindi or English using gTTS.
        Caches the generated MP3 bytes in memory (LRU) and on disk.
        Returns bytes or None if generation failed.
        """
        if not text or not text.strip():
            return None

        # Clean text of markdown asterisks/formatting before TTS
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").strip()
        lang_code = "hi" if language == "hi" else "en"

        # Unique cache key
        cache_key = hashlib.md5(f"{lang_code}:{clean_text}".encode("utf-8")).hexdigest()

        # 1. In-memory cache (fastest)
        cached = self._mem_cache_get(cache_key)
        if cached:
            return cached

        # 2. Disk cache
        cache_path = os.path.join(CACHE_DIR, f"{cache_key}.mp3")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as f:
                    data = f.read()
                if data:
                    self._mem_cache_put(cache_key, data)
                    return data
            except Exception:
                pass

        # 3. Generate via gTTS with single retry and a network timeout
        for attempt in range(2):
            try:
                tts = gTTS(text=clean_text, lang=lang_code, slow=False, timeout=10)
                buf = io.BytesIO()
                tts.write_to_fp(buf)
                audio_bytes = buf.getvalue()
                # Save to disk cache atomically (temp file + rename) so another thread
                # can never read a half-written MP3.
                try:
                    tmp_path = f"{cache_path}.{os.getpid()}.{threading.get_ident()}.tmp"
                    with open(tmp_path, "wb") as f:
                        f.write(audio_bytes)
                    os.replace(tmp_path, cache_path)
                except Exception:
                    pass
                # Save to memory cache
                self._mem_cache_put(cache_key, audio_bytes)
                return audio_bytes
            except Exception as e:
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                # If failed after 1 retry, return None (graceful fallback)
                return None

        return None

    def transcribe_audio_bytes(self, audio_bytes: bytes, language: str = "hi") -> Tuple[bool, str, Optional[float]]:
        """
        Transcribes speech audio bytes in Hindi ('hi') or English ('en').
        Returns: (success: bool, transcript_or_error: str, confidence: Optional[float])
        Note: Google free SpeechRecognition API does not return a confidence score,
        so confidence is set to None (we do not claim fake confidence).
        Retries failed external call at most once.
        """
        if not audio_bytes or len(audio_bytes) < 500:
            err = "आवाज़ बहुत छोटी थी, कृपया फिर से बोलें।" if language == "hi" else "Audio was too short or empty. Please speak again."
            return False, err, None

        lang_code = "hi-IN" if language == "hi" else "en-IN"

        for attempt in range(2):
            try:
                audio_io = io.BytesIO(audio_bytes)
                with sr.AudioFile(audio_io) as source:
                    audio_data = self.recognizer.record(source)

                # Recognize using Google Speech Recognition service
                transcript = self.recognizer.recognize_google(audio_data, language=lang_code)
                if transcript and transcript.strip():
                    return True, transcript.strip(), None
                else:
                    err = "आवाज़ स्पष्ट नहीं थी, कृपया पुनः बोलें।" if language == "hi" else "Speech was not clear. Please speak again."
                    return False, err, None

            except sr.UnknownValueError:
                err = "आवाज़ पहचानी नहीं जा सकी। कृपया साफ आवाज़ में दोबारा बोलें या नीचे लिखें।" if language == "hi" else "Could not understand the audio. Please speak clearly or type below."
                return False, err, None

            except sr.RequestError as e:
                if attempt == 0:
                    time.sleep(0.8)
                    continue
                err = f"इंटरनेट या ध्वनि सेवा में त्रुटि: {str(e)}। कृपया दोबारा कोशिश करें या नीचे लिखें।" if language == "hi" else f"Speech service network error: {str(e)}. Please retry or type below."
                return False, err, None

            except Exception as e:
                # E.g. Unsupported audio format / header issues
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                err = f"ध्वनि प्रारूप पढ़ने में समस्या: {str(e)}। कृपया नीचे दिए गए विकल्पों का उपयोग करें।" if language == "hi" else f"Could not read audio format: {str(e)}. Please use text input or buttons below."
                return False, err, None

        err = "ध्वनि सेवा उपलब्ध नहीं हो सकी।" if language == "hi" else "Speech service unavailable."
        return False, err, None


# Global singleton instance
speech_service = SpeechService()
