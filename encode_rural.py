from PIL import Image

# Convert text to binary string
def text_to_bin(text: str) -> str:
    return ''.join(format(ord(c), '08b') for c in text)

def encode_image(img: Image.Image, message: str) -> Image.Image:
    # Add a terminator to know when to stop decoding
    img = img.convert("RGB")
    message += "####"
    binary = text_to_bin(message)
    data_len = len(binary)

    # Open image
    #img = Image.open(input_path).convert("RGB")
    encoded = img.copy()
    pixels = encoded.load()

    width, height = img.size
    capacity = width * height * 3  # 3 bits per pixel

    # Safety check
    if data_len > capacity:
        raise ValueError("Message too large to fit in image!")

    data_index = 0
    for y in range(height):         # row-major order
        for x in range(width):
            if data_index >= data_len:
                #encoded.save(output_path)
                return encoded

            r, g, b = pixels[x, y]

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

    #encoded.save(output_path)
    return encoded