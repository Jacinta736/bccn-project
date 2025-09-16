import socket
from io import BytesIO
from PIL import Image
import numpy as np
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId

# ---------------- MongoDB Setup ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client["healthcare"]
patients = db["patients"]
fs = gridfs.GridFS(db)

# ---------------- Socket Setup ----------------
PORT = 12345
BUFFERSIZE = 1024
FILENAME = "received.png"

# ---------------- Receive Image ----------------
def receive_image(filename):
    s = socket.socket()
    s.bind(("0.0.0.0", PORT))
    s.listen(1)
    print("Waiting for doctor to send encoded image...")
    conn, addr = s.accept()
    print("Connected from", addr)

    with open(filename, "wb") as f:
        while True:
            data = conn.recv(BUFFERSIZE)
            if not data:
                break
            f.write(data)

    conn.close()
    s.close()
    print("Encoded image received & saved as", filename)

# ---------------- Decoding Helpers ----------------
def extract(pixels):
    bits = ""
    message = ""
    for row in pixels:
        for pixel in row:
            for value in pixel:
                bits += str(value & 1)
                if len(bits) == 8:  # full byte
                    char = chr(int(bits, 2))
                    message += char
                    if message.endswith("####"):  # stop at terminator
                        return message[:-4]  # strip terminator
                    bits = ""  # reset
    return message

def decode_image(path):
    img = Image.open(path)
    img = img.convert("RGB")
    pixels = np.array(img)
    return extract(pixels)

# ---------------- Integration with DB ----------------
def process_and_store(patient_id):
    # 1. Receive stego image
    receive_image(FILENAME)

    # 2. Decode hidden text
    hidden_message = decode_image(FILENAME)
    print("Decoded hidden message:", hidden_message)

    # 3. Save encoded image into GridFS
    with open(FILENAME, "rb") as f:
        file_bytes = f.read()
    gridfs_id = fs.put(file_bytes, filename=f"patient_{patient_id}_treatment.png")

    # 4. Update patient record
    update_data = {"gridfs_treatment_id": str(gridfs_id)}
    if "|" in hidden_message:
        parts = hidden_message.split("|")
        update_data["treatment_plan"] = parts[0].strip()
        if len(parts) > 1:
            update_data["medication"] = parts[1].strip()
    else:
        update_data["treatment_plan"] = hidden_message

    patients.update_one(
        {"_id": ObjectId(patient_id)},
        {"$set": update_data}
    )

    print(f"✅ Patient {patient_id} updated with new treatment plan!")

# ---------------- Run ----------------
if __name__ == "__main__":
    # Replace with actual patient_id from your DB
    patient_id = "650f8b1e1f9a1c1234567890"
    process_and_store(patient_id)
