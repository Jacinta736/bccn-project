# BCCN-project
BCCN group project using HTML, CSS, JavaScript, Python and MongoDB Atlas
# Roles
### Primary Physician (in rural area)
What the Physician Does:
- Captures or uploads an image.
- Inputs sensitive medical data.
- Embeds the sensitive medical data inside the image using steganography.
- Sends the stego-image across the hospital network.

What the Phisician Receives:
- A new stego-image containing the treatment plan, prescriptions, and medications provided by the hospital.
- Extracts the hidden response from it.

### Speacialized Doctors (in hospitals)
What the Doctor Does:
- Analyzes the patient’s condition.
- Prepares a treatment plan and prescription.
- Embeds the encrypted response inside a new image using steganography.
- Sends the new stego-image back to the patient through the network.

What the Doctor Receives:
- Receives the stego-image from the patient.
- Extracts the hidden medical data using steganography decoding to obtain patient details and medical information.

# Programming Languages
### HTML, CSS, JavaScript
- to create the webpage

### Python
- Socket- to transfer files
- Pillow- for image manipulation
- Flask- to connect webpage to python

### MongoDB
- Database- to store the image for future use