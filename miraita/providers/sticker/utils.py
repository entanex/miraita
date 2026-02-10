from pathlib import Path
from io import BytesIO


def get_img_data(file_path: str | Path, as_io: bool = False) -> bytes | BytesIO:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Sticker file not found: {path}")

    img_bytes = path.read_bytes()

    return BytesIO(img_bytes) if as_io else img_bytes
