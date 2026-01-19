#!/usr/bin/env python3
"""Create a placeholder logo for the PDF generator."""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing Pillow...")
    os.system("pip install Pillow")
    from PIL import Image, ImageDraw, ImageFont


def create_placeholder_logo():
    """Create a placeholder Infopercept logo."""
    # Create image
    width, height = 400, 120
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Draw background rectangle
    draw.rounded_rectangle(
        [(5, 5), (width - 5, height - 5)],
        radius=10,
        fill=(26, 54, 93, 255)  # Dark blue
    )

    # Add text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        except (OSError, IOError):
            font = ImageFont.load_default()

    text = "INFOPERCEPT"

    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center text
    x = (width - text_width) / 2
    y = (height - text_height) / 2 - 5

    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    # Save image
    assets_dir = Path(__file__).parent.parent / "app" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    logo_path = assets_dir / "infopercept_logo.png"
    img.save(logo_path, "PNG")

    print(f"Placeholder logo created at: {logo_path}")
    return logo_path


if __name__ == "__main__":
    create_placeholder_logo()
