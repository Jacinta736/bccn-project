from PIL import Image

# --- Helpers for decoding ---
def bin_to_text(binary):
    """Convert binary string to text until end marker."""
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
    """Extract hidden text from an encoded image."""
    img = image.convert("RGB")
    pixels = img.load()

    binary = ""
    for i in range(img.size[1]):
        for j in range(img.size[0]):
            r, g, b = pixels[j, i]
            binary += str(r & 1)
            binary += str(g & 1)
            binary += str(b & 1)

    return bin_to_text(binary)

# --- Test locally ---
if __name__ == "__main__":
    encoded_path = "static/uploads/encoded/Carlos Alcaraz_encoded.png"  # put actual name
    img = Image.open(encoded_path)
    hidden_message = decode_image(img)
    print("Decoded message:", hidden_message)
