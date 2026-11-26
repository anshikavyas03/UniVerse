import asyncio
import importlib
from pathlib import Path
import tempfile

from .providers import SpeechToTextProvider, TextToSpeechProvider, VoiceProviderError


class LocalWhisperProvider(SpeechToTextProvider):
    """Transcribe uploaded audio with the optional faster-whisper runtime."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                whisper = importlib.import_module("faster_whisper")
            except ImportError as error:
                raise VoiceProviderError("Speech recognition is unavailable. Install faster-whisper to enable local transcription.") from error
            self._model = whisper.WhisperModel(self.model_name, device="auto", compute_type="int8")
        return self._model

    async def transcribe(self, audio: bytes, language: str) -> str:
        if not audio:
            raise VoiceProviderError("The audio recording was empty.")
        suffix = ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as audio_file:
            audio_file.write(audio)
            audio_path = audio_file.name
        try:
            def run() -> str:
                segments, _ = self._load_model().transcribe(audio_path, language=None if language == "auto" else language)
                return " ".join(segment.text.strip() for segment in segments).strip()

            result = await asyncio.to_thread(run)
        except VoiceProviderError:
            raise
        except Exception as error:
            raise VoiceProviderError("Speech recognition could not load its local model. Verify WHISPER_MODEL and complete its initial download.") from error
        finally:
            Path(audio_path).unlink(missing_ok=True)
        if not result:
            raise VoiceProviderError("No speech was detected in the recording.")
        return result


class PiperTextToSpeechProvider(TextToSpeechProvider):
    """Create WAV speech through a locally installed Piper command and model."""

    def __init__(self, executable: str, english_model_path: str | None, hindi_model_path: str | None) -> None:
        self.executable = executable
        self.model_paths = {"en": english_model_path, "hi": hindi_model_path}

    async def synthesize(self, text: str, language: str) -> bytes:
        model_path = self.model_paths.get(language)
        if not model_path:
            raise VoiceProviderError(f"Text-to-speech is not configured for {language}. Set the matching Piper voice model path.")
        if not Path(model_path).is_file():
            raise VoiceProviderError(f"The configured {language} Piper voice model could not be found.")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
            output_path = output_file.name
        try:
            try:
                process = await asyncio.create_subprocess_exec(
                    self.executable, "--model", model_path, "--output_file", output_path,
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
            except FileNotFoundError as error:
                raise VoiceProviderError("Text-to-speech is unavailable. Install Piper or set PIPER_EXECUTABLE.") from error
            _, stderr = await process.communicate(text.encode("utf-8"))
            if process.returncode != 0:
                detail = stderr.decode("utf-8", errors="replace").strip()
                raise VoiceProviderError(f"Piper could not create speech{f': {detail}' if detail else '.'}")
            return Path(output_path).read_bytes()
        finally:
            Path(output_path).unlink(missing_ok=True)


class MacOSTextToSpeechProvider(TextToSpeechProvider):
    """Use macOS's installed Indian neural voices for the local demo experience."""

    def __init__(self, english_voice: str, hindi_voice: str) -> None:
        self.voices = {"en": english_voice, "hi": hindi_voice}

    async def synthesize(self, text: str, language: str) -> bytes:
        voice = self.voices.get(language)
        if not voice:
            raise VoiceProviderError(f"No macOS voice is configured for {language}.")
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as source_file, tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
            source_path, output_path = source_file.name, output_file.name
        Path(output_path).unlink(missing_ok=True)
        try:
            try:
                say_process = await asyncio.create_subprocess_exec("say", "-v", voice, "-o", source_path, text, stderr=asyncio.subprocess.PIPE)
                _, say_error = await say_process.communicate()
            except FileNotFoundError as error:
                raise VoiceProviderError("macOS text-to-speech is only available on macOS.") from error
            if say_process.returncode != 0:
                raise VoiceProviderError(f"macOS text-to-speech failed: {say_error.decode('utf-8', errors='replace').strip()}")
            convert_process = await asyncio.create_subprocess_exec("afconvert", "-f", "WAVE", "-d", "LEI16@22050", source_path, output_path, stderr=asyncio.subprocess.PIPE)
            _, convert_error = await convert_process.communicate()
            if convert_process.returncode != 0:
                raise VoiceProviderError(f"macOS audio conversion failed: {convert_error.decode('utf-8', errors='replace').strip()}")
            return Path(output_path).read_bytes()
        finally:
            Path(source_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
