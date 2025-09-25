# recognition.py
import os
import pickle
import numpy as np
import face_recognition
import cv2
import datetime
from db import get_connection  # your database connection

ENCODINGS_FILE = "encodings.pickle"
UNKNOWN_FACES_DIR = "uploads/unknown_faces"
  
# make sure the folder exists
os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)

def load_encodings():
    if not os.path.exists(ENCODINGS_FILE): 
        return {"encodings": [], "names": []}
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    return data

_data = load_encodings()
KNOWN_ENCODINGS = np.array(_data.get("encodings", []))
KNOWN_NAMES = list(_data.get("names", []))

def reload_encodings():
    global _data, KNOWN_ENCODINGS, KNOWN_NAMES
    _data = load_encodings()
    KNOWN_ENCODINGS = np.array(_data.get("encodings", []))
    KNOWN_NAMES = list(_data.get("names", []))
    return len(KNOWN_NAMES)

def log_unknown_face(filename, error_message):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (log_type, message) VALUES (%s, %s)",
        ("UnknownFace", f"{filename}: {error_message}")
    )
    conn.commit()
    cursor.close()
    conn.close()

def recognize_faces_in_image(image_path, tolerance=0.45, model='hog'):
    image = face_recognition.load_image_file(image_path)
    face_locations = face_recognition.face_locations(image, model=model)
    face_encodings = face_recognition.face_encodings(image, face_locations)

    results = []
    if KNOWN_ENCODINGS.size == 0:
        for loc in face_locations:
            results.append({"name": None, "distance": None, "location": loc})
        return results

    for loc, enc in zip(face_locations, face_encodings):
        distances = face_recognition.face_distance(KNOWN_ENCODINGS, enc)
        best_idx = int(np.argmin(distances))
        best_dist = float(distances[best_idx])
        if best_dist <= tolerance:
            name = KNOWN_NAMES[best_idx]
        else:
            name = None

            # --- LOG UNKNOWN FACE ---
            # save unknown face image
            top, right, bottom, left = loc
            unknown_face_img = image[top:bottom, left:right]
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"unknown_{timestamp}.jpg"
            save_path = os.path.join(UNKNOWN_FACES_DIR, filename)
            cv2.imwrite(save_path, cv2.cvtColor(unknown_face_img, cv2.COLOR_RGB2BGR))

            # log to database
            log_unknown_face(filename, "Face not recognized")
            # -----------------------

        results.append({"name": name, "distance": best_dist, "location": loc})
    return results

# # recognition.py
# import os
# import pickle
# import numpy as np
# import face_recognition

# ENCODINGS_FILE = "encodings.pickle"

# def load_encodings():
#     if not os.path.exists(ENCODINGS_FILE):
#         return {"encodings": [], "names": []}
#     with open(ENCODINGS_FILE, "rb") as f:
#         data = pickle.load(f)
#     return data

# _data = load_encodings()
# KNOWN_ENCODINGS = np.array(_data.get("encodings", []))
# KNOWN_NAMES = list(_data.get("names", []))

# def reload_encodings():
#     global _data, KNOWN_ENCODINGS, KNOWN_NAMES
#     _data = load_encodings()
#     KNOWN_ENCODINGS = np.array(_data.get("encodings", []))
#     KNOWN_NAMES = list(_data.get("names", []))
#     return len(KNOWN_NAMES)

# def recognize_faces_in_image(image_path, tolerance=0.45, model='hog'):
#     image = face_recognition.load_image_file(image_path)
#     face_locations = face_recognition.face_locations(image, model=model)
#     face_encodings = face_recognition.face_encodings(image, face_locations)

#     results = []
#     if KNOWN_ENCODINGS.size == 0:
#         for loc in face_locations:
#             results.append({"name": None, "distance": None, "location": loc})
#         return results

#     for loc, enc in zip(face_locations, face_encodings):
#         distances = face_recognition.face_distance(KNOWN_ENCODINGS, enc)
#         best_idx = int(np.argmin(distances))
#         best_dist = float(distances[best_idx])
#         if best_dist <= tolerance:
#             name = KNOWN_NAMES[best_idx]
#         else:
#             name = None
#         results.append({"name": name, "distance": best_dist, "location": loc})
#     return results












 # recognition.py
# import os
# import pickle
# import numpy as np
# import face_recognition

# ENCODINGS_FILE = "encodings.pickle"

# def load_encodings():
#     if not os.path.exists(ENCODINGS_FILE):
#         return {"encodings": [], "names": []}
#     with open(ENCODINGS_FILE, "rb") as f:
#         data = pickle.load(f)
#     return data

# # Load at import time (fast at runtime)
# _data = load_encodings()
# KNOWN_ENCODINGS = np.array(_data.get("encodings", []))
# KNOWN_NAMES = list(_data.get("names", []))

# def reload_encodings():
#     global _data, KNOWN_ENCODINGS, KNOWN_NAMES
#     _data = load_encodings()
#     KNOWN_ENCODINGS = np.array(_data.get("encodings", []))
#     KNOWN_NAMES = list(_data.get("names", []))
#     return len(KNOWN_NAMES)

# def recognize_faces_in_image(image_path, tolerance=0.45, model='hog'):
#     """
#     Returns a list of dicts, one per detected face:
#       { "name": <student_id or None>, "distance": <float>, "location": (top,right,bottom,left) }
#     """
#     image = face_recognition.load_image_file(image_path)
#     # choose model: 'hog' is faster, 'cnn' is more accurate (requires GPU / is slower)
#     face_locations = face_recognition.face_locations(image, model=model)
#     face_encodings = face_recognition.face_encodings(image, face_locations)

#     results = []
#     if KNOWN_ENCODINGS.size == 0:
#         # no encodings yet
#         for loc in face_locations:
#             results.append({"name": None, "distance": None, "location": loc})
#         return results

#     for loc, enc in zip(face_locations, face_encodings):
#         distances = face_recognition.face_distance(KNOWN_ENCODINGS, enc)  # lower = closer
#         best_idx = int(np.argmin(distances))
#         best_dist = float(distances[best_idx])
#         if best_dist <= tolerance:
#             name = KNOWN_NAMES[best_idx]
#         else:
#             name = None
#         results.append({"name": name, "distance": best_dist, "location": loc})
#     return results
















# import face_recognition
# import os
# from db import cursor

# STUDENT_FOLDER = os.getenv("STUDENT_IMAGES_FOLDER")

# def load_known_faces():
#     cursor.execute("SELECT * FROM students")
#     students = cursor.fetchall()
#     known_encodings = []
#     names = []

#     for stu in students:
#         img_path = stu['image_path']
#         img = face_recognition.load_image_file(img_path)
#         encoding = face_recognition.face_encodings(img)[0]
#         known_encodings.append(encoding)
#         names.append(stu['name'])
#     return known_encodings, names

# def recognize_faces(file_path):
#     unknown_image = face_recognition.load_image_file(file_path)
#     unknown_encodings = face_recognition.face_encodings(unknown_image)
    
#     known_encodings, names = load_known_faces()
    
#     results = []
#     for encoding in unknown_encodings:
#         matches = face_recognition.compare_faces(known_encodings, encoding)
#         name = "Unknown"
#         if True in matches:
#             first_match_index = matches.index(True)
#             name = names[first_match_index]
#         results.append(name)
#     return results

  