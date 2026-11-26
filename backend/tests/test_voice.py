import unittest

from app.services.voice.implementations import LocalWhisperProvider, PiperTextToSpeechProvider
from app.services.voice.providers import VoiceProviderError


class VoiceProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_audio_is_rejected_before_loading_whisper(self):
        with self.assertRaisesRegex(VoiceProviderError, "empty"):
            await LocalWhisperProvider("base").transcribe(b"", "en")

    def test_piper_is_the_default_text_to_speech_provider(self):
        provider = PiperTextToSpeechProvider("piper", None, None)
        self.assertEqual(provider.executable, "piper")
