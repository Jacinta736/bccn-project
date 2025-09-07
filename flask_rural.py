from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import os
from datetime import datetime
from bson.objectid import ObjectId
#import pytesseract
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from PIL import Image

app = Flask(__name__)

# MongoDB connection (local by default, can be replaced with Atlas URI)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["healthcare"]
patients = db["patients"]

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Dummy login credentials
users = {"doctor": "password123"}


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
    name_query = request.args.get("name")  # Get search input from form
    if name_query:
        # Case-insensitive search for partial matches
        all_patients = patients.find({"name": {"$regex": name_query, "$options": "i"}})
    else:
        all_patients = patients.find()
    return render_template("dashboard.html", patients=all_patients)


@app.route("/new_patient", methods=["GET", "POST"])
def new_patient():
    if request.method == "POST":
        image_file = request.files["image"]
        image_filename = None
        if image_file:
            image_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
            image_file.save(image_path)
            image_filename = image_file.filename

        patient_data = {
            "date": request.form["date"],
            "name": request.form["name"],
            "age": request.form["age"],
            "doctor": request.form["doctor"],
            "specialty": request.form["specialty"],
            "description": request.form["description"],
            "image": image_filename,
            "treatment_plan": None,
            "medication": None,
            "comments": []  # store multiple comments
        }
        patients.insert_one(patient_data)
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

        # Doctor’s comments
        comment_text = request.form.get("comment")
        comment_entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "comment": comment_text
        } if comment_text else None

        update_data = {}
        if extracted_text:
            # simple assumption: split extracted text
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
    app.run(debug=True)