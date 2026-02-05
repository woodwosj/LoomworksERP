#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate placeholder logo assets for Loomworks ERP.

This script creates simple placeholder PNG images for branding purposes.
These should be replaced with professionally designed assets later.

Requires: Pillow (pip install Pillow)
"""

import os
import struct
import zlib
from pathlib import Path


def create_png(width: int, height: int, bg_color: tuple, fg_color: tuple, text: str = None) -> bytes:
    """
    Create a simple PNG image with optional text placeholder.
    Uses pure Python - no external dependencies.
    """
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk_len = struct.pack('>I', len(data))
        chunk_crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
        return chunk_len + chunk_type + data + chunk_crc

    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr = png_chunk(b'IHDR', ihdr_data)

    # Create image data (simple solid color with pattern)
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # Filter type: None
        for x in range(width):
            # Create a simple pattern to make it recognizable as placeholder
            if (x < 2 or x >= width - 2 or y < 2 or y >= height - 2):
                # Border
                raw_data += bytes(fg_color)
            elif ((x + y) % 20 < 2) and text:
                # Simple pattern indicator
                raw_data += bytes(fg_color)
            else:
                raw_data += bytes(bg_color)

    # IDAT chunk (compressed image data)
    compressed = zlib.compress(raw_data, 9)
    idat = png_chunk(b'IDAT', compressed)

    # IEND chunk
    iend = png_chunk(b'IEND', b'')

    return signature + ihdr + idat + iend


def create_ico(sizes: list, bg_color: tuple, fg_color: tuple) -> bytes:
    """
    Create a simple ICO file with multiple sizes.
    """
    # ICO header
    ico_header = struct.pack('<HHH', 0, 1, len(sizes))

    entries = []
    image_data = []
    offset = 6 + len(sizes) * 16  # Header + entries

    for size in sizes:
        png_data = create_png(size, size, bg_color, fg_color, "L")

        # ICO directory entry
        entry = struct.pack(
            '<BBBBHHII',
            size if size < 256 else 0,  # Width
            size if size < 256 else 0,  # Height
            0,  # Color palette
            0,  # Reserved
            1,  # Color planes
            32,  # Bits per pixel
            len(png_data),  # Size of image data
            offset  # Offset to image data
        )
        entries.append(entry)
        image_data.append(png_data)
        offset += len(png_data)

    return ico_header + b''.join(entries) + b''.join(image_data)


def main():
    """Generate all placeholder assets."""
    assets_dir = Path(__file__).parent.parent / 'assets'
    assets_dir.mkdir(exist_ok=True)

    # Loomworks brand colors
    primary = (30, 58, 95)       # #1e3a5f - Deep blue
    secondary = (45, 212, 191)   # #2dd4bf - Teal
    white = (255, 255, 255)

    print("Generating placeholder logo assets...")

    # Main logo (200x50) - horizontal
    logo_data = create_png(200, 50, white, primary, "LOOMWORKS")
    with open(assets_dir / 'loomworks_logo.png', 'wb') as f:
        f.write(logo_data)
    print("  Created: loomworks_logo.png (200x50)")

    # White logo on transparent (simulate with primary bg)
    logo_white_data = create_png(200, 50, primary, white, "LOOMWORKS")
    with open(assets_dir / 'loomworks_logo_white.png', 'wb') as f:
        f.write(logo_white_data)
    print("  Created: loomworks_logo_white.png (200x50)")

    # Alternative logo
    logo_alt_data = create_png(200, 50, secondary, primary, "LOOMWORKS")
    with open(assets_dir / 'loomworks_logo_alt.png', 'wb') as f:
        f.write(logo_alt_data)
    print("  Created: loomworks_logo_alt.png (200x50)")

    # Tiny logo (62x20)
    logo_tiny_data = create_png(62, 20, white, primary, "LW")
    with open(assets_dir / 'loomworks_logo_tiny.png', 'wb') as f:
        f.write(logo_tiny_data)
    print("  Created: loomworks_logo_tiny.png (62x20)")

    # Square icons
    for size, name in [(64, 'loomworks_icon.png'),
                       (192, 'loomworks_icon_192.png'),
                       (512, 'loomworks_icon_512.png')]:
        icon_data = create_png(size, size, primary, secondary, "L")
        with open(assets_dir / name, 'wb') as f:
            f.write(icon_data)
        print(f"  Created: {name} ({size}x{size})")

    # iOS icon (180x180)
    ios_icon = create_png(180, 180, primary, secondary, "L")
    with open(assets_dir / 'loomworks_icon_ios.png', 'wb') as f:
        f.write(ios_icon)
    print("  Created: loomworks_icon_ios.png (180x180)")

    # Favicon (ICO with 16x16 and 32x32)
    favicon_data = create_ico([16, 32], primary, secondary)
    with open(assets_dir / 'loomworks_favicon.ico', 'wb') as f:
        f.write(favicon_data)
    print("  Created: loomworks_favicon.ico (16x16, 32x32)")

    # Module icon (128x128)
    module_icon = create_png(128, 128, primary, white, "LW")
    with open(assets_dir / 'loomworks_module_icon.png', 'wb') as f:
        f.write(module_icon)
    print("  Created: loomworks_module_icon.png (128x128)")

    print("\nAll placeholder assets generated successfully!")
    print("NOTE: These are simple placeholders. Replace with professionally designed logos.")


if __name__ == '__main__':
    main()
