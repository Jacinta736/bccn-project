import io
import gridfs

# connect GridFS
#fs = gridfs.GridFS(db)

# --- Helpers for encoding ---
def text_to_bin(text):
    return ''.join(format(ord(c), '08b') for c in text)

def encode_image(image, message):
    binary = text_to_bin(message) + '1111111111111110'
    data_index = 0

    img = image.convert('RGB')
    encoded = img.copy()
    pixels = encoded.load()

    for i in range(img.size[0]):
        for j in range(img.size[1]):
            if data_index >= len(binary):
                return encoded   # stop encoding once done
            r, g, b = pixels[i, j]
            if data_index < len(binary):
                r = (r & ~1) | int(binary[data_index])
                data_index += 1
            if data_index < len(binary):
                g = (g & ~1) | int(binary[data_index])
                data_index += 1
            if data_index < len(binary):
                b = (b & ~1) | int(binary[data_index])
                data_index += 1
            pixels[i, j] = (r, g, b)
    return encoded
