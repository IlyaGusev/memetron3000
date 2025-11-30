from pathlib import Path
from PIL import Image


def create_thumbnail(
    image_path: Path, thumbnail_path: Path, max_size: int = 400, quality: int = 85
) -> None:
    """
    Create a thumbnail from an image.

    Args:
        image_path: Path to the original image
        thumbnail_path: Path where thumbnail should be saved
        max_size: Maximum dimension (width or height) for the thumbnail
        quality: JPEG quality (1-100)
    """
    with Image.open(image_path) as img:
        # Convert RGBA to RGB if needed
        if img.mode == "RGBA":
            # Create a white background
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Calculate new size while maintaining aspect ratio
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Save thumbnail with compression
        img.save(thumbnail_path, "JPEG", quality=quality, optimize=True)
