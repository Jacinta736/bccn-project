from flask import Flask, render_template, request, redirect, url_for, send_file
from pymongo import MongoClient
import os, io
from datetime import datetime
from bson.objectid import ObjectId
from PIL import Image
from encode_hospital import encode_image
import gridfs
import socket

app = Flask(__name__, template_folder='templates', static_folder='uploads')

# ---------------- MongoDB Setup ----------------
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client["telemedicine_db"]
patients = db["patients"]
fs = gridfs.GridFS(db)

UPLOAD_FOLDER = "hospital/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Dummy doctor login
users = {"doctor": "password123"}

# Socket configuration for rural transmission
RURAL_HOST = "127.0.0.1"
RURAL_PORT = 12345  # Must match rural receiver port
BUFFER_SIZE = 1024

# ---------------- Socket Helper ----------------
def send_image_to_rural(image_path):
    """Send encoded image to rural system via socket"""
    try:
        s = socket.socket()
        s.connect((RURAL_HOST, RURAL_PORT))
        
        # Send file content
        with open(image_path, "rb") as f:
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                s.send(chunk)
        
        s.close()
        print(f"✅ Image sent to rural center at {RURAL_HOST}:{RURAL_PORT}")
        return True
    except Exception as e:
        print(f"❌ Error sending image to rural: {e}")
        return False


# ---------------- Routes ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username] == password:
            return redirect(url_for("dashboard"))
        return "Invalid login! Try again."
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    data = list(patients.find())
    return render_template("dashboard.html", patients=data)


@app.route("/patient/<id>", methods=["GET", "POST"])
def view_patient(id):
    patient = patients.find_one({"_id": ObjectId(id)})
    if not patient:
        return "Patient not found!"

    if request.method == "POST":
        # Doctor submits treatment plan + medication
        treatment = request.form.get("treatment", "").strip()
        medication = request.form.get("medication", "").strip()

        if not treatment and not medication:
            return "Please provide treatment plan or medication!"

        # Get original image from GridFS
        image_field = patient.get("gridfs_id")
        if not image_field:
            return "No image found for this patient!"
            
        try:
            image_bytes = fs.get(ObjectId(image_field)).read()
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            return f"Error retrieving image: {e}"

        # Encode treatment info into image
        message = f"Treatment:{treatment}|Medication:{medication}"
        encoded_img = encode_image(img, message)

        # Save encoded treatment image to disk
        treatment_filename = f"treatment_{patient['_id']}.png"
        treatment_path = os.path.join(UPLOAD_FOLDER, treatment_filename)
        encoded_img.save(treatment_path)

        # Save to GridFS as well
        img_io = io.BytesIO()
        encoded_img.save(img_io, "PNG")
        img_io.seek(0)
        treatment_image_id = fs.put(img_io, filename=treatment_filename)

        # Update patient record
        patients.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "treatment_plan": treatment,
                "medication": medication,
                "treatment_image_id": str(treatment_image_id)
            }}
        )

        # Send image back to rural
        print(f"Sending treatment image to rural center...")
        success = send_image_to_rural(treatment_path)
        if success:
            print("✅ Treatment image sent successfully")
        else:
            print("❌ Failed to send treatment image")

        return redirect(url_for("dashboard"))

    return render_template("patient_details.html", patient=patient)


@app.route("/treatment/<id>")
def treatment(id):
    patient = patients.find_one({"_id": ObjectId(id)})
    if not patient:
        return "Patient not found!"
    data = list(patients.find())
    return render_template("treatment_page.html", patients=data, current_patient=patient)


@app.route("/image/<id>")
def get_image(id):
    patient = patients.find_one({"_id": ObjectId(id)})
    if not patient:
        return "Image not found!"
    
    image_field = patient.get("gridfs_id")
    if not image_field:
        return "No image found for this patient!"
    
    try:
        image_bytes = fs.get(ObjectId(image_field)).read()
        return send_file(io.BytesIO(image_bytes), mimetype="image/png")
    except Exception as e:
        return f"Error retrieving image: {e}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)