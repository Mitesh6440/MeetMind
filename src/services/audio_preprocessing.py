from pathlib import Path
from shutil import which
from typing import Optional
from pydub import AudioSegment, effects
import os

# Target format for STT 
TARGET_SAMPLE_RATE = 16_000   # 16 kHz
TARGET_CHANNELS = 1           # Mono
TARGET_FORMAT = "wav"         # Export format

class AudioPreprocessingError(Exception):
    """Custom exception for errors during audio preprocessing."""
    pass


def load_audio(input_path : Path) -> AudioSegment:
    """
    Load an audio file using pydub.
    pydub uses ffmpeg under the hood, so ffmpeg must be installed.
    """

    # Try to find ffmpeg in system PATH first
    ffmpeg_exe = which("ffmpeg")
    ffprobe_exe = which("ffprobe")
    
    # If not in PATH, try common installation locations (configurable via env var)
    if not ffmpeg_exe:
        ffmpeg_path = os.environ.get("FFMPEG_PATH", "")
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            ffmpeg_exe = os.path.join(ffmpeg_path, "ffmpeg.exe")
            ffprobe_exe = os.path.join(ffmpeg_path, "ffprobe.exe")
    
    # Set pydub's converter if found
    if ffmpeg_exe and os.path.exists(ffmpeg_exe):
        AudioSegment.converter = ffmpeg_exe
    if ffprobe_exe and os.path.exists(ffprobe_exe):
        AudioSegment.ffprobe = ffprobe_exe
    
    if not input_path.exists():
        raise AudioPreprocessingError(f"Input file not found: {input_path}")
    
    try :
        audio = AudioSegment.from_file(str(input_path))
        return audio
    except Exception as e:
        raise AudioPreprocessingError(f"Failed to load audio: {e}")
    

def apply_normalization(audio : AudioSegment) -> AudioSegment :
    """
    Normalize the audio to a standard loudness level.
    This helps STT models perform better.
    """
    return effects.normalize(audio)


def apply_basic_noise_reduction(audio : AudioSegment) -> AudioSegment :
    """
    Very simple noise reduction using filters.
    This is NOT advanced AI noise reduction, but
    it helps cut low hum and very high hiss.
    """

    # Remove very low frequencies (< 100 Hz) - rumble / hum
    audio = audio.high_pass_filter(100)

    # Remove ultra high frequencies (> 8000 Hz) - hiss
    audio = audio.low_pass_filter(8000)

    return audio


def convert_to_target_format(audio : AudioSegment) -> AudioSegment :
    """
    Convert audio to mono, 16 kHz sample rate for compatibility
    with most speech-to-text systems.
    """

    if audio.channels != TARGET_CHANNELS :
        audio = audio.set_channels(TARGET_CHANNELS)

    if audio.frame_rate != TARGET_SAMPLE_RATE:
        audio = audio.set_frame_rate(TARGET_SAMPLE_RATE)

    return audio


def preprocess_audio_file(input_path : Path, output_dir : Optional[Path] = None, enable_noise_reduction : bool = True) :
    """
    Full preprocessing pipeline:

    1. Load audio
    2. basic noise reduction
    3. Normalize loudness
    4. Convert to mono, 16 kHz
    5. Export as WAV to output_dir

    Returns:
        Path to the preprocessed audio file.
    """

    if output_dir is None:
        output_dir = input_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load
    audio = load_audio(input_path)

    # 2. Noise reduction (simple filters)
    if enable_noise_reduction:
        audio = apply_basic_noise_reduction(audio)

    # 3. Normalize
    audio = apply_normalization(audio)

    # 4. Convert to target format (channels + sample rate)
    audio = convert_to_target_format(audio)

    # 5. Export as WAV
    output_path = output_dir / f"{input_path.stem}_processed.{TARGET_FORMAT}"
    try:
        audio.export(output_path, format=TARGET_FORMAT)
    except Exception as e:
        raise AudioPreprocessingError(f"Failed to export processed audio: {e}")

    return output_path