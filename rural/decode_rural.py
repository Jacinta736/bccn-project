import socket
from io import BytesIO
from PIL import Image
import numpy as np
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
import os

# ---------------- MongoDB Setup ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client["healthcare"]
patients = db["patients"]
fs = gridfs.GridFS(db)

# ---------------- Socket Setup ----------------
PORT = 12345
BUFFERSIZE = 1024
FILENAME = "rural/uploads/treatment_received.png"

# ---------------- Receive Image ----------------
def receive_image(filename):
    """Receive treatment image from hospital via socket"""
    s = socket.socket()
    s.bind(("0.0.0.0", PORT))  # Listen on all interfaces
    s.listen(1)
    print(f"🏥 Rural center listening for treatment on port {PORT}...")
    conn, addr = s.accept()
    print(f"📩 Connected from {addr}")

    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "wb") as f:
        while True:
            data = conn.recv(BUFFERSIZE)
            if not data:
                break
            f.write(data)

    conn.close()
    s.close()
    print(f"✅ Treatment image received & saved as {filename}")
    return filename

# ---------------- Decoding Helpers ----------------
def bin_to_text(binary):
    """Convert binary string to text until end marker"""
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
    """Extract hidden text from an encoded image"""
    img = image.convert("RGB")
    pixels = img.load()
    binary = ""
    
    for y in range(img.size[1]):  # height
        for x in range(img.size[0]):  # width
            r, g, b = pixels[x, y]
            binary += str(r & 1)
            binary += str(g & 1)
            binary += str(b & 1)
    
    return bin_to_text(binary)

# ---------------- Integration with DB ----------------
def process_and_store(patient_id):
    """Receive treatment image and update patient record"""
    # 1. Receive stego image
    received_path = receive_image(FILENAME)

    # 2. Decode hidden text
    img = Image.open(received_path)
    hidden_message = decode_image(img)
    print(f"✅ Decoded treatment message: {hidden_message}")

    # 3. Save encoded image into GridFS
    with open(received_path, "rb") as f:
        file_bytes = f.read()
    gridfs_id = fs.put(file_bytes, filename=f"patient_{patient_id}_treatment.png")

    # 4. Parse and update patient record
    update_data = {"gridfs_treatment_id": str(gridfs_id)}
    
    # Parse format: "Treatment:XXX|Medication:YYY"
    if "|" in hidden_message:
        parts = hidden_message.split("|")
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if key == "treatment":
                    update_data["treatment_plan"] = value
                elif key == "medication":
                    update_data["medication"] = value
    else:
        # Fallback if format is different
        update_data["treatment_plan"] = hidden_message

    patients.update_one(
        {"_id": ObjectId(patient_id)},
        {"$set": update_data}
    )

    print(f"✅ Patient {patient_id} updated with treatment plan!")
    return update_data

# ---------------- Run ----------------
if __name__ == "__main__":
    print("🏥 Rural Treatment Receiver Active")
    print("Waiting for treatment data from hospital...")
    
    # You need to provide the actual patient_id
    # This could be retrieved from command line or config
    import sys
    if len(sys.argv) > 1:
        patient_id = sys.argv[1]
    else:
        # Get the most recently added patient without treatment
        patient = patients.find_one(
            {"treatment_plan": None}, 
            sort=[("_id", -1)]
        )
        if patient:
            patient_id = str(patient["_id"])
            print(f"📋 Auto-detected patient: {patient.get('name', 'Unknown')} (ID: {patient_id})")
        else:
            print("❌ No patients found without treatment. Please specify patient ID.")
            sys.exit(1)
    
    process_and_store(patient_id)
    print("\n🎉 Treatment received and stored successfully!")