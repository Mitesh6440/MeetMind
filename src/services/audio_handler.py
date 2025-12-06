from pathlib import Path
from uuid import uuid4

class AudioValidationError(Exception):
    """Custom exception raised when an audio file fails validation."""
    pass

# Allowed audio formats
ALLOWED_AUDIO_EXTENSIONS : set[str] = {".wav",".mp3",".m4a"}

# Basic size limit
MAX_AUDIO_SIZE_MB : float = 25.0


def get_extension(filename : str) -> str :
    """Return lowercased file extension (including dot)."""
    return Path(filename).suffix.lower()


def validate_audio_extension(filename : str) -> None :
    """
    Validate that the audio file has an allowed extension.

    Raises:
        AudioValidationError: if extension is not allowed.
    """
    extension = get_extension(filename)
    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise AudioValidationError(
            f"Unsupported audio format '{extension}'. "
            f"Allowed formats are: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}."
        )


def validate_audio_size(file_bytes : float) -> None :
    """
    Validate that the audio size is within acceptable limits and not empty.

    Raises:
        AudioValidationError: if size is 0 or exceeds MAX_AUDIO_SIZE_MB.
    """
    size_bytes = len(file_bytes)
    if size_bytes == 0:
        raise AudioValidationError("Audio file is empty.")

    size_mb = size_bytes / (1024 * 1024)
    if size_mb > MAX_AUDIO_SIZE_MB:
        raise AudioValidationError(
            f"Audio file is too large ({size_mb:.2f} MB). "
            f"Maximum allowed size is {MAX_AUDIO_SIZE_MB:.2f} MB."
        )
    

def validate_audio_basic(filename : str , file_bytes : float) -> None :
    """
    Perform basic validation:
    - extension check
    - size check

    Raises:
        AudioValidationError: if any check fails.
    """
    validate_audio_extension(filename)
    validate_audio_size(file_bytes)


def save_audio_file(original_filename : str , file_bytes : float , upload_dir : Path) -> Path:
    """
    Validate and save uploaded audio file to `upload_dir` with a unique name.

    Returns:
        Path to the saved audio file.

    Raises:
        AudioValidationError: if validation fails.
    """

    # 1. Validate
    validate_audio_basic(original_filename,file_bytes)

    # 2. Ensure upload directory exists
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 3. Generate unique file name to avoid clashes
    extension = get_extension(original_filename)
    unique_name = f"{uuid4().hex}{extension}"
    file_path = upload_dir / unique_name

    # 4. Save bytes to file
    file_path.write_bytes(file_bytes)
    print(file_path)
    return file_path