import os
import cv2
import face_recognition
import pickle

# Path where student images are stored
STUDENT_IMAGES_DIR = "student_images/"
ENCODINGS_FILE = "encodings.pickle"

known_encodings = []
known_names = []

print("[INFO] Processing student images...")

# Loop through each image in student_images/
for filename in os.listdir(STUDENT_IMAGES_DIR):
    if filename.endswith((".jpg", ".png", ".jpeg")):
        name = os.path.splitext(filename)[0]  # Student name = file name
        filepath = os.path.join(STUDENT_IMAGES_DIR, filename)

        # Load image
        image = cv2.imread(filepath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detect face and compute encodings
        boxes = face_recognition.face_locations(rgb, model="hog")  # or "cnn" for more accuracy
        encodings = face_recognition.face_encodings(rgb, boxes)

        for encoding in encodings:
            known_encodings.append(encoding)
            known_names.append(name)

        print(f"[OK] Processed {filename} -> {name}")

# Save encodings to file
data = {"encodings": known_encodings, "names": known_names}
with open(ENCODINGS_FILE, "wb") as f:
    pickle.dump(data, f)

print(f"[DONE] Encodings saved to {ENCODINGS_FILE}")
