from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import os
from datetime import datetime
from bson.objectid import ObjectId
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from PIL import Image
from encode_rural import encode_image
import gridfs, io, socket

app = Flask(__name__, template_folder='templates', static_folder='uploads')

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["healthcare"]
patients = db["patients"]
fs = gridfs.GridFS(db)

UPLOAD_FOLDER = "rural/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Dummy login credentials
users = {"doctor": "password123"}

# Socket config (for sending encoded image to hospital)
HOSPITAL_HOST = "127.0.0.1"
HOSPITAL_PORT = 12346  # Hospital receiver port

# ---------------- Socket Helper ----------------
def send_image_to_hospital(image_path):
    """Send encoded image to hospital via socket"""
    try:
        s = socket.socket()
        s.connect((HOSPITAL_HOST, HOSPITAL_PORT))

        with open(image_path, "rb") as f:
            while True:
                data = f.read(1024)
                if not data:
                    break
                s.send(data)
        s.close()
        print(f"✅ Image sent to hospital at {HOSPITAL_HOST}:{HOSPITAL_PORT}")
        return True
    except Exception as e:
        print(f"❌ Error sending image: {e}")
        return False
    
# ---------------- Routes ---------------- #

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username] == password:
            return redirect(url_for("dashboard"))
        else:
            return "Invalid credentials. Try again."
    return render_template("login.html")


@app.route("/dashboard", methods=["GET"])
def dashboard():
    name_query = request.args.get("name")
    if name_query:
        all_patients = patients.find({"name": {"$regex": name_query, "$options": "i"}})
    else:
        all_patients = patients.find()
    return render_template("dashboard.html", patients=all_patients)


@app.route("/new_patient", methods=["GET", "POST"])
def new_patient():
    if request.method == "POST":
        image_file = request.files.get("image")
        image_filename = None
        gridfs_id = None
        
        patient_data = {
            "date": request.form["date"],
            "name": request.form["name"],
            "age": request.form["age"],
            "doctor": request.form["doctor"],
            "specialty": request.form["specialty"],
            "description": request.form["description"],
            "image": None,
            "treatment_plan": None,
            "medication": None,
            "comments": [],
            "gridfs_id": None
        }

        if image_file:
            # Save original image
            image_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
            image_file.save(image_path)
            
            # Create message to encode
            img = Image.open(image_path)
            message = f"Name:{patient_data['name']}|Age:{patient_data['age']}|Doctor:{patient_data['doctor']}|Specialty:{patient_data['specialty']}|Description:{patient_data['description']}"
            
            # Encode message into image
            encoded_img = encode_image(img, message)

            # Save encoded image to BytesIO
            img_io = io.BytesIO()
            encoded_img.save(img_io, "PNG")
            img_io.seek(0)

            # Save in GridFS
            gridfs_id = fs.put(img_io, filename=f"{patient_data['name']}_encoded.png")
            patient_data["gridfs_id"] = str(gridfs_id)
            patient_data["image"] = f"{patient_data['name']}_encoded.png"

            # Save encoded image to disk for socket transmission
            encoded_path = os.path.join(UPLOAD_FOLDER, f"{patient_data['name']}_encoded.png")
            img_io.seek(0)
            with open(encoded_path, "wb") as f:
                f.write(img_io.getbuffer())

            # Send encoded image to hospital
            print(f"Attempting to send image to hospital...")
            success = send_image_to_hospital(encoded_path)
            if success:
                print("✅ Image successfully sent to hospital")
            else:
                print("❌ Failed to send image to hospital")

        # Insert patient record
        inserted = patients.insert_one(patient_data)
        print(f"✅ Patient {patient_data['name']} created with ID: {inserted.inserted_id}")
        
        return redirect(url_for("dashboard"))
    
    return render_template("new_patient.html")


@app.route("/patient/<patient_id>", methods=["GET", "POST"])
def treatment_plan(patient_id):
    patient = patients.find_one({"_id": ObjectId(patient_id)})

    if request.method == "POST":
        # If doctor uploads new treatment image
        image_file = request.files.get("treatment_image")
        extracted_text = ""
        if image_file:
            image_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
            image_file.save(image_path)
            # OCR to extract text
            extracted_text = pytesseract.image_to_string(Image.open(image_path))

        # Doctor's comments
        comment_text = request.form.get("comment")
        comment_entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "comment": comment_text
        } if comment_text else None

        update_data = {}
        if extracted_text:
            # Parse extracted text
            parts = extracted_text.split("\n")
            update_data["treatment_plan"] = parts[0] if len(parts) > 0 else ""
            update_data["medication"] = parts[1] if len(parts) > 1 else ""

        if comment_entry:
            patients.update_one(
                {"_id": ObjectId(patient_id)},
                {"$push": {"comments": comment_entry}}
            )

        if update_data:
            patients.update_one(
                {"_id": ObjectId(patient_id)},
                {"$set": update_data}
            )

        return redirect(url_for("dashboard"))

    return render_template("treatment_plan.html", patient=patient)


# ---------------- Run App ---------------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)