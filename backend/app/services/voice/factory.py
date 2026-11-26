from ...core.config import Settings
from .implementations import LocalWhisperProvider, MacOSTextToSpeechProvider, PiperTextToSpeechProvider
from .providers import SpeechToTextProvider, TextToSpeechProvider, VoiceProviderError


def build_speech_to_text_provider(settings: Settings) -> SpeechToTextProvider:
    return LocalWhisperProvider(settings.whisper_model)


def build_text_to_speech_provider(settings: Settings) -> TextToSpeechProvider:
    if settings.tts_provider == "piper":
        return PiperTextToSpeechProvider(settings.piper_executable, settings.piper_english_model, settings.piper_hindi_model)
    if settings.tts_provider == "macos":
        return MacOSTextToSpeechProvider(settings.macos_english_voice, settings.macos_hindi_voice)
    raise VoiceProviderError(f"Unsupported TTS provider: {settings.tts_provider}")
