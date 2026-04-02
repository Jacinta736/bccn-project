from PIL import Image

def text_to_bin(text: str) -> str:
    """Convert text to binary string"""
    return ''.join(format(ord(c), '08b') for c in text)

def encode_image(img: Image.Image, message: str) -> Image.Image:
    """Encode message into image using LSB steganography"""
    # Convert to RGB if needed
    img = img.convert("RGB")
    
    # Add terminator to mark end of message
    message += "####"
    binary = text_to_bin(message)
    data_len = len(binary)

    # Create copy to avoid modifying original
    encoded = img.copy()
    pixels = encoded.load()

    width, height = img.size
    capacity = width * height * 3  # 3 bits per pixel (R, G, B)

    # Check if message fits
    if data_len > capacity:
        raise ValueError(f"Message too large ({data_len} bits) to fit in image (capacity: {capacity} bits)!")

    # Encode message into LSBs
    data_index = 0
    for y in range(height):
        for x in range(width):
            if data_index >= data_len:
                return encoded

            r, g, b = pixels[x, y]

            # Encode into LSB of each channel
            if data_index < data_len:
                r = (r & ~1) | int(binary[data_index])
                data_index += 1
            if data_index < data_len:
                g = (g & ~1) | int(binary[data_index])
                data_index += 1
            if data_index < data_len:
                b = (b & ~1) | int(binary[data_index])
                data_index += 1

            pixels[x, y] = (r, g, b)

    return encoded