"""
JanSahayak Configurable LLM Service
Supports Google Gemini (via google-genai) and OpenAI (via openai).
If no API key is set or the external call fails after 1 retry, falls back to an explicitly labeled
Deterministic Scripted Mode so the hackathon reviewer can test immediately without credentials.
"""

import os
import json
import math
import re
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# Per-call timeout for live LLM requests.
# NOTE: google-genai's types.HttpOptions(timeout=...) is in MILLISECONDS,
# whereas the OpenAI SDK's `timeout` is in SECONDS.
_LLM_TIMEOUT_SECONDS = 15
_GEMINI_TIMEOUT_MS = _LLM_TIMEOUT_SECONDS * 1000

# Used only when a 429 carries NO server-provided delay. Doubles on each
# consecutive hint-less 429 (capped) so we never hammer a throttled endpoint.
_DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS = 60.0
_MAX_DEFAULT_COOLDOWN_SECONDS = 600.0

# ---------------------------------------------------------------------------
# Rate-limit helpers (module level so they are easy to unit test)
# ---------------------------------------------------------------------------
_UNIT_SECONDS = {
    "ms": 0.001, "millisecond": 0.001, "milliseconds": 0.001,
    "s": 1.0, "sec": 1.0, "secs": 1.0, "second": 1.0, "seconds": 1.0,
    "m": 60.0, "min": 60.0, "mins": 60.0, "minute": 60.0, "minutes": 60.0,
    "h": 3600.0, "hr": 3600.0, "hrs": 3600.0, "hour": 3600.0, "hours": 3600.0,
}
_UNIT_RE = r"(?:ms|milliseconds?|hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)"
# One or more "<number><unit>" parts: 37.5s | 20ms | 6m0s | 1h2m3.5s | 30 seconds
_DURATION_RE = r"(?:\d+(?:\.\d+)?\s*" + _UNIT_RE + r"(?![a-z])\s*)+"
_DURATION_PART_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(" + _UNIT_RE + r")(?![a-z])", re.IGNORECASE)

# "Please retry in 37.559665956s." / "try again in 20ms" / "wait 60 seconds" / "retry after 2 minutes"
_PHRASE_DELAY_RE = re.compile(
    r"(?:retry|try\s+again|wait)\s*(?:in|after|for)?\s*[:=]?\s*(" + _DURATION_RE + r")",
    re.IGNORECASE,
)
# Google RetryInfo: 'retryDelay': '37s'   (also "retry_delay")
_RETRY_DELAY_KEY_RE = re.compile(
    r"retry_?delay['\"]?\s*[:=]\s*['\"]?(" + _DURATION_RE + r")", re.IGNORECASE
)
# "Retry-After: 30"  /  "retry-after-ms: 1500"  (bare numbers: seconds, or ms for the -ms header)
_RETRY_AFTER_RE = re.compile(
    r"retry[-_ ]after(-ms)?['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)(?:\s*(" + _UNIT_RE + r")(?![a-z]))?",
    re.IGNORECASE,
)
_RATE_LIMIT_TEXT_RE = re.compile(
    r"\b429\b|RESOURCE_EXHAUSTED|rate[\s_-]*limit|too\s+many\s+requests|"
    r"quota\s+(?:exceeded|exhausted)|exceeded\s+your\s+current\s+quota",
    re.IGNORECASE,
)


def _duration_to_seconds(text: str) -> Optional[float]:
    """Sum every '<number><unit>' part in `text` (e.g. '1h2m3.5s' -> 3723.5)."""
    parts = _DURATION_PART_RE.findall(text or "")
    if not parts:
        return None
    return sum(float(num) * _UNIT_SECONDS[unit.lower()] for num, unit in parts)


def _walk_for_retry_delay(obj: Any, found: list, depth: int = 0) -> None:
    """Collect Google RetryInfo 'retryDelay' values from nested dict/list error details."""
    if depth > 6:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower().replace("_", "") == "retrydelay" and isinstance(v, (str, int, float)):
                secs = _duration_to_seconds(v) if isinstance(v, str) else float(v)
                if secs is not None:
                    found.append(secs)
            else:
                _walk_for_retry_delay(v, found, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _walk_for_retry_delay(item, found, depth + 1)


def _header_get(headers: Any, name: str) -> Optional[str]:
    try:
        val = headers.get(name)
        if val is None:
            val = headers.get(name.title())
        return None if val is None else str(val)
    except Exception:
        return None


def is_rate_limit_error(error: Exception) -> bool:
    """True only for genuine HTTP 429 / quota errors (not any message containing 'rate')."""
    for attr in ("code", "status_code", "http_status", "status"):
        val = getattr(error, attr, None)
        if val == 429 or (isinstance(val, str) and val.strip().upper() in ("429", "RESOURCE_EXHAUSTED")):
            return True
    resp = getattr(error, "response", None)
    if resp is not None and getattr(resp, "status_code", None) == 429:
        return True
    if "ratelimit" in type(error).__name__.lower():
        return True
    return bool(_RATE_LIMIT_TEXT_RE.search(str(error)))


def parse_retry_delay_seconds(error: Exception) -> Optional[float]:
    """
    Extract the server-requested wait (seconds) from a 429 error, or None if the
    server gave no hint. Understands:
      * Retry-After / retry-after-ms response headers (seconds, ms, or HTTP-date)
      * Google RetryInfo.retryDelay ('37s', '37.559665956s') in structured details or text
      * Free-text: 'Please retry in 37.5s', 'try again in 20ms', 'wait 60 seconds', '6m0s'
    When several hints exist the LONGEST wins, and the result is rounded UP to a whole
    second. Server delays are never capped, so we can never retry earlier than asked.
    """
    candidates: list = []

    # 1. Response headers (httpx / requests style objects)
    resp = getattr(error, "response", None)
    headers = getattr(resp, "headers", None)
    if headers is not None:
        ms = _header_get(headers, "retry-after-ms")
        if ms:
            try:
                candidates.append(float(ms) / 1000.0)
            except ValueError:
                pass
        ra = _header_get(headers, "retry-after")
        if ra:
            ra = ra.strip()
            try:
                candidates.append(float(ra))
            except ValueError:
                try:  # HTTP-date form
                    dt = parsedate_to_datetime(ra)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    candidates.append(max(0.0, (dt - datetime.now(timezone.utc)).total_seconds()))
                except Exception:
                    pass

    # 2. Structured details (google-genai APIError.details / .response_json)
    for attr in ("details", "response_json"):
        details = getattr(error, attr, None)
        if details:
            _walk_for_retry_delay(details, candidates)

    # 3. Text of the error message
    text = str(error)
    for m in _RETRY_DELAY_KEY_RE.finditer(text):
        secs = _duration_to_seconds(m.group(1))
        if secs is not None:
            candidates.append(secs)
    for m in _PHRASE_DELAY_RE.finditer(text):
        secs = _duration_to_seconds(m.group(1))
        if secs is not None:
            candidates.append(secs)
    for m in _RETRY_AFTER_RE.finditer(text):
        is_ms_header, num, unit = m.group(1), float(m.group(2)), m.group(3)
        if unit:
            candidates.append(num * _UNIT_SECONDS[unit.lower()])
        else:
            candidates.append(num / 1000.0 if is_ms_header else num)

    candidates = [c for c in candidates if c is not None and c >= 0 and math.isfinite(c)]
    if not candidates:
        return None
    return float(math.ceil(max(candidates)))


class LLMService:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash").strip()
        self.provider = "none"

        if self.gemini_api_key:
            self.provider = "gemini"
        elif self.openai_api_key:
            self.provider = "openai"

        self.fallback_active = False
        self.last_fallback_reason: Optional[str] = None

        # Rate-limit cooldown (shared by all Streamlit sessions: the quota belongs to the API key).
        # `_rate_limit_until` is a time.monotonic() deadline; 0.0 means "not cooling down".
        self._lock = threading.RLock()
        self._rate_limit_until: float = 0.0
        self._fallback_due_to_rate_limit = False
        self._consecutive_hintless_429s = 0

        # Reusable SDK clients (lazily created so a missing SDK still degrades gracefully)
        self._gemini_client = None
        self._openai_client = None

    # ------------------------------------------------------------------
    # Fallback / rate-limit state
    # ------------------------------------------------------------------
    def trigger_fallback(self, reason: str, rate_limited: bool = False) -> None:
        """Mark provider as having fallen back to scripted demo mode."""
        with self._lock:
            self.fallback_active = True
            self.last_fallback_reason = reason
            self._fallback_due_to_rate_limit = rate_limited

    def reset_fallback(self) -> None:
        """Reset fallback state after a successful live call. Never overrides an active cooldown."""
        with self._lock:
            if self._rate_limit_until and time.monotonic() < self._rate_limit_until:
                return
            self.fallback_active = False
            self.last_fallback_reason = None
            self._fallback_due_to_rate_limit = False

    def _cooldown_remaining(self) -> float:
        """Seconds left in a rate-limit cooldown. Auto-recovers (clears the 429 fallback) once elapsed."""
        with self._lock:
            if not self._rate_limit_until:
                return 0.0
            remaining = self._rate_limit_until - time.monotonic()
            if remaining > 0:
                return remaining
            # Cooldown elapsed: allow live calls again without a restart.
            self._rate_limit_until = 0.0
            if self._fallback_due_to_rate_limit:
                self.fallback_active = False
                self.last_fallback_reason = None
                self._fallback_due_to_rate_limit = False
            return 0.0

    def _enter_rate_limit_cooldown(self, error: Exception, provider_label: str) -> float:
        """Start (or extend, never shorten) a cooldown using the server's retry delay."""
        hinted = parse_retry_delay_seconds(error)
        with self._lock:
            if hinted is not None:
                wait = hinted
                self._consecutive_hintless_429s = 0
            else:
                wait = min(
                    _DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS * (2 ** self._consecutive_hintless_429s),
                    _MAX_DEFAULT_COOLDOWN_SECONDS,
                )
                self._consecutive_hintless_429s += 1
            self._rate_limit_until = max(self._rate_limit_until, time.monotonic() + wait)
            self.trigger_fallback(f"{provider_label} rate limit (429)", rate_limited=True)
            return wait

    def _on_live_success(self) -> None:
        with self._lock:
            self._consecutive_hintless_429s = 0
        self.reset_fallback()

    def get_provider_status(self, language: str = "en") -> Dict[str, Any]:
        """Returns the current runtime LLM status clearly indicating live AI or scripted demo mode."""
        is_hi = (language == "hi")
        # Auto-recover from an expired 429 cooldown BEFORE deciding which mode to report,
        # otherwise a stale fallback flag would keep every caller on the scripted path forever.
        cooldown_left = self._cooldown_remaining()
        # If external service failed and fell back, report honestly
        if self.fallback_active:
            reason = self.last_fallback_reason or ("बाहरी एपीआई कॉल विफल रही" if is_hi else "External API call failed after retry")
            if cooldown_left > 0:
                secs = int(math.ceil(cooldown_left))
                reason += (f"; लाइव एआई ~{secs} सेकंड बाद फिर कोशिश करेगा" if is_hi
                           else f"; live AI will be retried in ~{secs}s")
            label_en = f"🟡 Scripted Demo Mode (Live AI failed: {reason}; fallen back to deterministic engine)"
            label_hi = f"🟡 स्क्रिप्टेड डेमो मोड (लाइव एआई त्रुटि: {reason}; ऑफ़लाइन इंजन सक्रिय)"
            return {
                "active": False,
                "provider": "Scripted Rule-Based Engine",
                "model": "rule_based_deterministic_fallback",
                "is_scripted_fallback": True,
                "label": label_hi if is_hi else label_en,
                "label_hi": label_hi,
                "label_en": label_en
            }

        if self.provider == "gemini":
            label_en = f"🟢 Live AI Active (Google Gemini - {self.model_name})"
            label_hi = f"🟢 लाइव एआई सक्रिय (Google Gemini - {self.model_name})"
            return {
                "active": True,
                "provider": "Google Gemini",
                "model": self.model_name,
                "is_scripted_fallback": False,
                "label": label_hi if is_hi else label_en,
                "label_hi": label_hi,
                "label_en": label_en
            }
        elif self.provider == "openai":
            label_en = f"🟢 Live AI Active (OpenAI - {self.model_name})"
            label_hi = f"🟢 लाइव एआई सक्रिय (OpenAI - {self.model_name})"
            return {
                "active": True,
                "provider": "OpenAI",
                "model": self.model_name if "gpt" in self.model_name else "gpt-4o-mini",
                "is_scripted_fallback": False,
                "label": label_hi if is_hi else label_en,
                "label_hi": label_hi,
                "label_en": label_en
            }
        else:
            label_en = "🟡 Scripted Demo Mode (No API key found in .env; deterministic logic active)"
            label_hi = "🟡 स्क्रिप्टेड डेमो मोड (.env में कोई एपीआई कुंजी नहीं मिली; ऑफ़लाइन इंजन सक्रिय)"
            return {
                "active": False,
                "provider": "Scripted Rule-Based Engine",
                "model": "rule_based_deterministic_fallback",
                "is_scripted_fallback": True,
                "label": label_hi if is_hi else label_en,
                "label_hi": label_hi,
                "label_en": label_en
            }

    def _get_gemini_client(self):
        """Cached Gemini client with a hard per-request timeout (HttpOptions.timeout is in ms)."""
        if self._gemini_client is None:
            from google import genai
            from google.genai import types
            self._gemini_client = genai.Client(
                api_key=self.gemini_api_key,
                http_options=types.HttpOptions(timeout=_GEMINI_TIMEOUT_MS),
            )
        return self._gemini_client

    def _get_openai_client(self):
        """Cached OpenAI client. max_retries=0 so the SDK cannot silently retry a 429 before our cooldown."""
        if self._openai_client is None:
            import openai
            self._openai_client = openai.OpenAI(
                api_key=self.openai_api_key,
                timeout=_LLM_TIMEOUT_SECONDS,
                max_retries=0,
            )
        return self._openai_client

    def generate_chat_response(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.2
    ) -> Tuple[bool, str, str]:
        """
        Generates text using the configured LLM API with single-retry resilience.
        Returns: (success: bool, response_text: str, provider_used: str)
        """
        # Honour a rate-limit cooldown: never touch the API before the server-requested delay elapses.
        if self._cooldown_remaining() > 0:
            return False, "", "Scripted Demo Fallback"

        # Try Gemini if configured
        if self.provider == "gemini":
            last_err = ""
            for attempt in range(2):
                try:
                    client = self._get_gemini_client()
                    full_prompt = f"{system_prompt}\n\nUser Message: {user_message}"
                    response = client.models.generate_content(
                        model=self.model_name if "gemini" in self.model_name else "gemini-2.5-flash",
                        contents=full_prompt,
                    )
                    if response and response.text:
                        self._on_live_success()
                        return True, response.text.strip(), "Google Gemini"
                except Exception as e:
                    last_err = str(e)
                    if is_rate_limit_error(e):
                        # No in-call retry on 429: wait out the server's delay, serve scripted meanwhile.
                        self._enter_rate_limit_cooldown(e, "Gemini")
                        break
                    if attempt == 0:
                        time.sleep(1.0)
                        continue
                    # Failed after retry, trigger fallback
                    self.trigger_fallback(f"Gemini API error: {last_err}")
                    break

        # Try OpenAI if configured
        elif self.provider == "openai":
            last_err = ""
            for attempt in range(2):
                try:
                    client = self._get_openai_client()
                    model_to_use = self.model_name if "gpt" in self.model_name else "gpt-4o-mini"
                    response = client.chat.completions.create(
                        model=model_to_use,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        temperature=temperature,
                    )
                    content = response.choices[0].message.content
                    if content:
                        self._on_live_success()
                        return True, content.strip(), "OpenAI"
                except Exception as e:
                    last_err = str(e)
                    if is_rate_limit_error(e):
                        self._enter_rate_limit_cooldown(e, "OpenAI")
                        break
                    if attempt == 0:
                        time.sleep(1.0)
                        continue
                    self.trigger_fallback(f"OpenAI API error: {last_err}")
                    break

        # Scripted fallback
        return False, "", "Scripted Demo Fallback"

    def extract_structured_slots(
        self,
        user_utterance: str,
        current_profile: Dict[str, Any],
        language: str = "hi"
    ) -> Dict[str, Any]:
        """
        Extracts customer profile slots from user utterance:
        - name, location, occupation, purpose, income_bracket, age
        If live LLM is active, uses LLM with JSON schema.
        Otherwise or on failure, uses deterministic regex/keyword parser.
        """
        system_prompt = (
            "You are an information extraction assistant for JanSahayak, an accessible banking app in India. "
            "Extract any of the following fields present in the user utterance: "
            "name, location (village/town/city), occupation (e.g. farmer, daily wage earner, driver, homemaker, shopkeeper), "
            "purpose (e.g. open savings account, get government subsidy, pension, insurance, safe savings), "
            "income_bracket, approximate age. "
            "Return ONLY a valid JSON object with keys: name, location, occupation, purpose, income_bracket, age. "
            "If a field is not mentioned, use null."
        )

        status = self.get_provider_status()
        if not status["is_scripted_fallback"]:
            success, raw_resp, provider = self.generate_chat_response(system_prompt, user_utterance)
            if success:
                try:
                    clean = re.sub(r"^```json\s*", "", raw_resp)
                    clean = re.sub(r"```$", "", clean).strip()
                    parsed = json.loads(clean)
                    # Merge non-null extracted fields
                    extracted = {}
                    for k in ["name", "location", "occupation", "purpose", "income_bracket", "age"]:
                        val = parsed.get(k)
                        if val and str(val).strip().lower() not in ["null", "none", "unknown", ""]:
                            extracted[k] = str(val).strip()
                    if extracted:
                        return extracted
                except Exception as e:
                    self.trigger_fallback(f"LLM JSON parsing error: {str(e)}")

        # Deterministic Scripted Fallback Extraction
        return self._rule_based_slot_extraction(user_utterance, current_profile, language)

    def _rule_based_slot_extraction(
        self,
        text: str,
        current_profile: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """Deterministic, reliable slot extractor for offline/scripted demo mode."""
        extracted: Dict[str, Any] = {}
        t_low = text.lower().strip()

        # Name extraction patterns
        # Hindi: मेरा नाम रमेश है / नाम सुरेश
        # English: my name is Ramesh / I am Ramesh
        name_patterns = [
            r"(?:मेरा\s*नाम|नाम)\s*(?:है)?\s*[:=\-]?\s*([a-zA-Z\u0900-\u097F]+)",
            r"(?:my\s*name\s*is|i\s*am|this\s*is)\s*([a-zA-Z]+)",
            r"(?:call\s*me)\s*([a-zA-Z]+)"
        ]
        for pat in name_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                extracted["name"] = m.group(1).strip().capitalize()
                break

        # Location extraction patterns
        # Handle "रामपुर गाँव / रामपुर शहर" or "गाँव रामपुर" or "live in Rampur / from Rampur"
        stop_words = {"में", "का", "के", "की", "से", "हूँ", "हू", "है", "था", "थी", "to", "the", "in", "from", "at", "and", "aur", "mein"}
        loc_patterns = [
            r"([a-zA-Z\u0900-\u097F]{2,20})\s*(?:गाँव|गांव|शहर|कस्बा)",
            r"(?:गाँव|गांव|शहर|कस्बा)\s*([a-zA-Z\u0900-\u097F]{2,20})",
            r"(?:रहने\s*वाला|रहती\s*हूँ|निवासी)\s*([a-zA-Z\u0900-\u097F]{2,20})",
            r"(?:live\s*in|living\s*in|from|village|town|city)\s*([a-zA-Z]{2,20})"
        ]
        for pat in loc_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                if candidate.lower() not in stop_words:
                    extracted["location"] = candidate.capitalize()
                    break

        # Occupation matching
        if language == "en":
            occupations = {
                "Farmer": ["farmer", "kisan", "खेती", "किसान", "agriculture"],
                "Daily Wage Earner": ["daily wage", "labor", "labour", "mazdoor", "मजदूर", "मजदूरी", "दिहाड़ी"],
                "Shopkeeper": ["shopkeeper", "dukan", "दुकान", "व्यापार", "business", "vendor"],
                "Homemaker": ["homemaker", "housewife", "गृहणी", "घर का काम"],
                "Driver": ["driver", "ड्राइवर", "गाड़ी चालक"],
                "Artisan": ["artisan", "carpenter", "tailor", "दर्जी", "बढ़ई", "कारीगर"]
            }
        else:
            occupations = {
                "किसान": ["farmer", "kisan", "खेती", "किसान", "agriculture"],
                "मजदूर / दैनिक वेतनभोगी": ["daily wage", "labor", "labour", "mazdoor", "मजदूर", "मजदूरी", "दिहाड़ी"],
                "दुकानदार": ["shopkeeper", "dukan", "दुकान", "व्यापार", "business", "vendor"],
                "गृहणी": ["homemaker", "housewife", "गृहणी", "घर का काम"],
                "ड्राइवर": ["driver", "ड्राइवर", "गाड़ी चालक"],
                "कारीगर": ["artisan", "carpenter", "tailor", "दर्जी", "बढ़ई", "कारीगर"]
            }
        for occ_label, kw_list in occupations.items():
            if any(kw in t_low for kw in kw_list):
                extracted["occupation"] = occ_label
                break

        # Purpose matching
        if language == "en":
            purposes = {
                "Government Subsidies & DBT": ["subsidy", "dbt", "pm kisan", "ration", "सरकारी", "सब्सिडी", "पैसा आता है"],
                "Safe Savings": ["savings", "save", "बचत", "जमा", "पैसे बचाना"],
                "Old Age Pension": ["pension", "old age", "बुढ़ापा", "पेंशन", "रिटायर"],
                "Life / Accident Insurance": ["insurance", "bima", "बीमा", "सुरक्षा", "दुर्घटना"]
            }
        else:
            purposes = {
                "सरकारी योजना व सब्सिडी": ["subsidy", "dbt", "pm kisan", "ration", "सरकारी", "सब्सिडी", "पैसा आता है"],
                "सुरक्षित बचत": ["savings", "save", "बचत", "जमा", "पैसे बचाना"],
                "बुढ़ापे की पेंशन": ["pension", "old age", "बुढ़ापा", "पेंशन", "रिटायर"],
                "परिवार का बीमा": ["insurance", "bima", "बीमा", "सुरक्षा", "दुर्घटना"]
            }
        for purp_label, kw_list in purposes.items():
            if any(kw in t_low for kw in kw_list):
                extracted["purpose"] = purp_label
                break

        # If user explicitly states they want to open an account
        if "account" in t_low or "खाता" in t_low or "बैंक" in t_low:
            if "purpose" not in extracted:
                extracted["purpose"] = "Open New Bank Account" if language == "en" else "नया बैंक खाता खोलना"

        return extracted


# Global singleton instance
llm_service = LLMService()
