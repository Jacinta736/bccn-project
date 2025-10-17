from PIL import Image

# ---------------- Decoding Helpers ----------------
def bin_to_text(binary):
    chars = []
    for i in range(0, len(binary), 8):
        byte = binary[i:i+8]
        if len(byte) < 8:
            break
        chars.append(chr(int(byte, 2)))
        if "".join(chars).endswith("####"):
            return "".join(chars)[:-4]
    return "".join(chars)


def decode_image(image):
    img = image.convert("RGB")
    pixels = img.load()
    binary = ""

    for y in range(img.size[1]):
        for x in range(img.size[0]):
            r, g, b = pixels[x, y]
            binary += str(r & 1)
            binary += str(g & 1)
            binary += str(b & 1)

    return bin_to_text(binary)

