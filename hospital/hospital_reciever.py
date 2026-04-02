import socket
from PIL import Image
from pymongo import MongoClient
import gridfs
from decode_hospital import decode_image
import os

# ---------------- Configuration ----------------
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 12346      # Must match what rural sends to
BUFFER_SIZE = 1024
SAVE_PATH = "hospital/uploads/received_from_rural.png"

# ---------------- MongoDB Setup ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client["telemedicine_db"]
patients = db["patients"]
fs = gridfs.GridFS(db)

# ---------------- Helper Functions ----------------
def receive_image():
    """Receive encoded image from rural center via socket"""
    s = socket.socket()
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"🏥 Hospital listening for image on port {PORT}...")
    conn, addr = s.accept()
    print(f"📩 Connection established from {addr}")

    os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
    with open(SAVE_PATH, "wb") as f:
        while True:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            f.write(data)

    conn.close()
    s.close()
    print(f"✅ Image received and saved as {SAVE_PATH}")
    return SAVE_PATH


def process_image(file_path):
    """Decode the steganographic image and store result in MongoDB"""
    img = Image.open(file_path)
    hidden_text = decode_image(img)
    print("✅ Decoded message from image:\n", hidden_text)

    # Parse the decoded data (expecting format like "Name:John|Age:45|...")
    patient_data = {}
    for pair in hidden_text.split("|"):
        if ":" in pair:
            key, value = pair.split(":", 1)
            patient_data[key.strip().lower()] = value.strip()

    # Store image in MongoDB (using GridFS)
    with open(file_path, "rb") as f:
        image_id = fs.put(f, filename=os.path.basename(file_path))
    
    # Create patient record with consistent field naming
    patient_record = {
        "decoded_data": hidden_text,
        "gridfs_id": str(image_id),
        "name": patient_data.get("name", "Unknown"),
        "age": patient_data.get("age", "N/A"),
        "doctor": patient_data.get("doctor", "N/A"),
        "specialty": patient_data.get("specialty", "N/A"),
        "description": patient_data.get("description", "N/A"),
        "treatment_plan": None,
        "medication": None,
        "treatment_image_id": None
    }
    
    result = patients.insert_one(patient_record)
    print(f"✅ Patient record created with ID: {result.inserted_id}")
    return hidden_text


# ---------------- Main Routine ----------------
if __name__ == "__main__":
    print("🏥 Hospital Receiver Active")
    img_path = receive_image()
    process_image(img_path)
    print("\n🎉 Transfer complete! Data successfully received and decoded.")