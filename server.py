from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os, subprocess, sys
import io
import pickle, face_recognition
import pandas as pd
from werkzeug.utils import secure_filename
from recognition import recognize_faces_in_image, reload_encodings
from db import save_student, save_attendance, get_connection  # ✅ DB functions
from attendance_export import export_attendance_to_excel
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}}, supports_credentials=True)
# CORS(app, supports_credentials=True)


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==========================
# Role check
# ==========================
def get_role():
    role = request.headers.get("Role", "")
    return role.lower()


# @app.route('/add-student', methods=['POST'])
# def add_student_route():
#     if get_role() != "admin":
#         return jsonify({"error": "unauthorized"}), 403

#     data = request.json
#     student_id = save_student(
#         name=data.get("name"),
#         roll_no=data.get("roll_no"),
#         branch=data.get("branch"),
#         section=data.get("section"),
#         year=data.get("year"),
#         passout_year=data.get("passout_year")
#     )
#     if student_id:
#         return jsonify({
#             "student_id": student_id,
#             "name": data.get("name"),
#             "roll_no": data.get("roll_no"),
#             "branch": data.get("branch"),
#             "section": data.get("section"),
#             "year": data.get("year"),
#             "passout_year": data.get("passout_year"),
#             "encoding_status": "pending"
#         })
#     return jsonify({"error": "failed to save student"}), 500

@app.route('/rebuild-encodings', methods=['POST'])
def rebuild_encodings_route():
    if get_role() != "admin":
        return jsonify({"error": "unauthorized"}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, photo_path FROM students WHERE photo_path IS NOT NULL")
    students = cursor.fetchall()
    cursor.close()
    conn.close()

    encodings = []
    names = []

    for student in students:
        name, photo_path = student
        if os.path.exists(photo_path):
            image = face_recognition.load_image_file(photo_path)
            face_enc = face_recognition.face_encodings(image)
            if face_enc:
                encodings.append(face_enc[0])
                names.append(name)

    # Save encodings
    with open("encodings.pickle", "wb") as f:
        pickle.dump({"encodings": encodings, "names": names}, f)

    return jsonify({"message": "Encodings rebuilt", "count": len(names)})

UPLOAD_FOLDER = "uploads/unknown_faces"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # make sure folder exists

@app.route('/add-student', methods=['POST'])
def add_student_route():
    try:
        if get_role() != "admin":
            return jsonify({"error": "unauthorized"}), 403

        # Initialize variables
        photo_path = None

        # 1️⃣ Check if FormData with photo
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                filename = secure_filename(photo.filename)
                photo_path = os.path.join(UPLOAD_FOLDER, filename)
                photo.save(photo_path)

            # Read other fields from form
            name = request.form.get("name", "")
            roll_no = request.form.get("roll_no", "")
            branch = request.form.get("branch", "")
            section = request.form.get("section", "")
            year = request.form.get("year", "")
            passout_year = request.form.get("passout_year", "")

        else:
            # 2️⃣ JSON request (no photo)
            data = request.get_json(force=True)
            name = data.get("name", "")
            roll_no = data.get("roll_no", "")
            branch = data.get("branch", "")
            section = data.get("section", "")
            year = data.get("year", "")
            passout_year = data.get("passout_year", "")

        # Save student in DB
        student_id = save_student(
            name=name,
            roll_no=roll_no,
            branch=branch,
            section=section,
            year=year,
            passout_year=passout_year,
            photo_path=photo_path
        )

        if not student_id:
            return jsonify({"error": "Failed to save student"}), 500

        return jsonify({
            "student_id": student_id,
            "name": name,
            "roll_no": roll_no,
            "branch": branch,
            "section": section,
            "year": year,
            "passout_year": passout_year,
            "photo_path": photo_path,
            "encoding_status": "pending"
        }), 200

    except Exception as e:
        print("❌ Error in /add-student:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/students/<roll_no>", methods=["PUT"])
def update_student(roll_no):
    data = request.json
    new_name = data.get("name")
    new_branch = data.get("branch")
    new_section = data.get("section")
    new_year = data.get("year")
    new_passout_year = data.get("passout_year")

    if not new_name:
        return jsonify({"error": "Name is required"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE students
            SET name = %s, branch = %s, section = %s, year = %s, passout_year = %s
            WHERE roll_no = %s
        """, (new_name, new_branch, new_section, new_year, new_passout_year, roll_no))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Student not found"}), 404
        return jsonify({"message": "Student updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin-stats')
def admin_stats():
    # Query total students and total attendance from DB
    conn = get_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as totalStudents FROM students")
        total_students = cursor.fetchone()["totalStudents"]
        cursor.execute("SELECT COUNT(*) as totalAttendance FROM attendance")
        total_attendance = cursor.fetchone()["totalAttendance"]
    finally:
        cursor.close()
        conn.close()
    return jsonify({
        "totalStudents": total_students,
        "attendanceRecords": total_attendance,
        "lastBackup": "Not implemented",
        "systemHealth": "Good"
    })


@app.route('/attendance-report', methods=['GET'])
def attendance_report_route():
    # Only admins can access
    if get_role() != "admin":
        return jsonify({"error": "unauthorized"}), 403

    conn = get_connection()
    if conn is None:
        return jsonify({"error": "DB connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        # Aggregate attendance per class per date
        cursor.execute("""
            SELECT 
                s.section AS class,
                a.date,
                SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) AS present,
                SUM(CASE WHEN a.status='absent' THEN 1 ELSE 0 END) AS absent,
                COUNT(*) AS total,
                ROUND(SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS percentage
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            GROUP BY class, a.date
            ORDER BY a.date DESC, class ASC
        """)

        rows = cursor.fetchall()

        # Convert datetime.date to string for JSON
        for row in rows:
            if isinstance(row['date'], (datetime, )):
                row['date'] = row['date'].strftime('%Y-%m-%d')

        return jsonify({"attendance": rows})

    finally:
        cursor.close()
        conn.close()

@app.route('/export-attendance', methods=['GET'])
def export_attendance_route():
    if get_role() != "admin":
        return jsonify({"error": "unauthorized"}), 403

    conn = get_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        # Fetch all raw attendance records
        cursor.execute("""
            SELECT 
                s.name,
                s.roll_no AS studentId,
                s.section AS class,
                a.date,
                a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            ORDER BY a.date DESC, class ASC
        """)
        rows = cursor.fetchall()

        # Export to Excel using pandas
        df = pd.DataFrame(rows)
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"attendance_export_{timestamp}.xlsx"

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )
    finally:
        cursor.close()
        conn.close()

@app.route('/export-attendance-archive', methods=['GET'])
def export_attendance():
    if get_role() != "admin":
        return jsonify({"error": "unauthorized"}), 403

    conn = get_connection()
    if conn is None:
        return jsonify({"error": "DB connection failed"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.name, s.roll_no, s.branch, s.section, a.date, a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
        """)
        rows = cursor.fetchall()

        import pandas as pd
        import io
        from flask import send_file

        df = pd.DataFrame(rows)
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return send_file(output,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         as_attachment=True,
                         download_name="attendance_export.xlsx")
    finally:
        cursor.close()
        conn.close()


@app.route('/backup-database', methods=['POST'])
def backup_database():
    if get_role() != "admin":
        return jsonify({"error": "unauthorized"}), 403
    # Example using mysqldump
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    cmd = f"mysqldump -u root -pvrinda487 smartattendance > backups/{filename}"
    os.makedirs("backups", exist_ok=True)
    subprocess.run(cmd, shell=True)
    return jsonify({"status": "success", "filename": filename, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

@app.route('/rebuild-encodings', methods=['POST'])
def rebuild_encodings():
    if get_role() != 'admin':
        return jsonify({"error": "unauthorized"}), 403
    try:
        p = subprocess.run([sys.executable, "encode_faces.py"], capture_output=True, text=True)
        count = reload_encodings()
        return jsonify({"status": "success", "encodings_loaded": count, "stdout": p.stdout})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================
# SYSTEM LOGS ROUTE
# ==========================
@app.route("/system-logs", methods=['GET'])
def system_logs():
    # Only admins can access
    if get_role() != "admin":
        return jsonify({"error": "unauthorized"}), 403

    logs = []
    try:
        # Check if log file exists
        if os.path.exists("system.log"):
            with open("system.log", "r") as f:
                for i, line in enumerate(f.readlines()):
                    # Each log is an object with keys used by frontend
                    logs.append({
                        "log_id": i,
                        "log_time": datetime.now().isoformat(),  # or parse timestamp if in file
                        "log_type": "info",  # default type, can extend later
                        "category": "system",  # default category
                        "message": line.strip()
                    })
        # Return as JSON object
        return jsonify({"logs": logs})
    except Exception as e:
        # In case of any error, still return JSON
        return jsonify({"logs": [], "error": str(e)}), 500






@app.route('/students', methods=['GET'])
def get_students_route():
    try:
        if get_role() != "admin":
            return jsonify({"error": "unauthorized"}), 403

        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT student_id AS id,
                   name,
                   roll_no,
                   branch,
                   section,
                   year,
                   passout_year,
                   'active' AS status,
                   'pending' AS encoding_status,
                   NULL AS last_seen
            FROM students
        """)
        rows = cursor.fetchall()
        return jsonify({"students": rows}), 200

    except Exception as e:
        print("❌ Error in /students:", e)
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass



@app.route('/upload-photo/<user_id>', methods=['POST'])
def upload_photo(user_id):
    if get_role() != "teacher":
        return jsonify({"error": "unauthorized"}), 403

    if 'image' not in request.files:
        return jsonify({"error": "no file uploaded"}), 400

    f = request.files['image']
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # ✅ ensure folder exists
    save_path = os.path.join(UPLOAD_FOLDER, f.filename)
    f.save(save_path)

    try:
        # Run recognition
        results = recognize_faces_in_image(save_path)

        # If no encodings exist, handle gracefully
        if results is None:
            results = []

    except Exception as e:
        # ✅ Log the error to terminal for debugging
        print("❌ Face recognition error:", str(e))
        return jsonify({"error": "Face recognition failed", "details": str(e)}), 500

    # ✅ Always return a list
    if not isinstance(results, list):
        results = []

    return jsonify(results), 200

@app.route('/delete-student/<roll_no>', methods=['DELETE'])
def delete_student(roll_no):
    try:
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor()

        # Check if student exists
        cursor.execute("SELECT * FROM students WHERE roll_no = %s", (roll_no,))
        student = cursor.fetchone()
        if not student:
            cursor.close()
            conn.close()
            return jsonify({"error": "Student not found"}), 404

        # Delete student
        cursor.execute("DELETE FROM students WHERE roll_no = %s", (roll_no,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": f"Student with roll_no {roll_no} deleted successfully"})
    except Exception as e:
        print("Error deleting student:", e)
        return jsonify({"error": str(e)}), 500



@app.route('/')
def index():
    return jsonify({"message": "Smart Attendance Flask API is running ✅"})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    print("DEBUG request JSON:", data)  # for debugging
    print("DEBUG headers:", request.headers)

    username = data.get('username')  # frontend sends username
    password = data.get('password')  # frontend sends password
    role = request.headers.get('Role', '').lower()  # Role header

    # check all fields
    if not username or not password or not role:
        return jsonify({"error": "Missing fields"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Check against your users table
        cursor.execute(
            "SELECT user_id, password_hash, role FROM users WHERE user_id=%s AND password_hash=%s AND role=%s",
            (int(username), password, role.capitalize())
        )
        user = cursor.fetchone()

        if user:
            return jsonify({
                "user_id": user["user_id"],
                "name": user.get("user_id"),  # you don’t have a separate name column
                "role": user["role"]
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    finally:
        cursor.close()
        conn.close()


# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")



1
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import os, subprocess, sys
# from recognition import recognize_faces_in_image, reload_encodings
# from db import save_student, save_attendance   # ✅ import the DB functions

# app = Flask(__name__)
# CORS(app)

# UPLOAD_FOLDER = "uploads"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# @app.route('/upload', methods=['POST'])
# def upload_image():
#     if 'image' not in request.files:
#         return jsonify({"error": "no image file"}), 400
#     f = request.files['image']
#     save_path = os.path.join(UPLOAD_FOLDER, f.filename)
#     f.save(save_path)

#     try:
#         matches = recognize_faces_in_image(save_path, tolerance=0.45, model='hog')
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

#     present = []
#     for m in matches:
#         if m['name'] is not None:
#             # ✅ save recognized student & attendance
#             student_id = save_student(m['name'], m.get('roll_no', None), m.get('encoding'))
#             if student_id:
#                 save_attendance(student_id, recognized=True)
#                 present.append(m['name'])

#     unknowns = sum(1 for m in matches if m['name'] is None)

#     return jsonify({
#         "matches": matches,
#         "present_count": len(present),
#         "unknown_count": unknowns
#     })


# @app.route('/train', methods=['POST'])
# def train_route():
#     # run the training script and reload encodings
#     p = subprocess.run([sys.executable, "encode_faces.py"], capture_output=True, text=True)
#     count = reload_encodings()
#     return jsonify({"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "encodings_loaded": count})


# if __name__ == "__main__":
#     app.run(debug=True, host="0.0.0.0")






# # server.py (minimal version)
# from flask import Flask, request, jsonify, send_file
# from flask_cors import CORS
# import os, subprocess, sys
# from recognition import recognize_faces_in_image, reload_encodings

# app = Flask(__name__)
# CORS(app)

# UPLOAD_FOLDER = "uploads"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# @app.route('/upload', methods=['POST'])
# def upload_image():
#     if 'image' not in request.files:
#         return jsonify({"error": "no image file"}), 400
#     f = request.files['image']
#     save_path = os.path.join(UPLOAD_FOLDER, f.filename)
#     f.save(save_path)

#     try:
#         matches = recognize_faces_in_image(save_path, tolerance=0.45, model='hog')
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

#     # Example response (you should also save to DB using your db helper)
#     present = [m['name'] for m in matches if m['name'] is not None]
#     unknowns = sum(1 for m in matches if m['name'] is None)
#     return jsonify({"matches": matches, "present_count": len(present), "unknown_count": unknowns})

# @app.route('/train', methods=['POST'])
# def train_route():
#     # run the training script and reload encodings
#     p = subprocess.run([sys.executable, "encode_faces.py"], capture_output=True, text=True)
#     count = reload_encodings()
#     return jsonify({"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "encodings_loaded": count})

# if __name__ == "__main__":
#     app.run(debug=True, host="0.0.0.0")





# from flask import Flask, request, jsonify, send_file
# from flask_cors import CORS
# import os
# from db import db, cursor
# import recognition
# import attendance_export
# from dotenv import load_dotenv

# load_dotenv()

# app = Flask(__name__)
# CORS(app)
# app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER")
# app.config["STUDENT_IMAGES_FOLDER"] = os.getenv("STUDENT_IMAGES_FOLDER")

# # Add student
# @app.route("/students", methods=["POST"])
# def add_student():
#     data = request.form
#     file = request.files['image']
#     file_path = os.path.join(app.config["STUDENT_IMAGES_FOLDER"], file.filename)
#     file.save(file_path)

#     cursor.execute( 
#         "INSERT INTO students (name, roll, branch, section, passoutYear, image_path) VALUES (%s,%s,%s,%s,%s,%s)",
#         (data['name'], data['roll'], data['branch'], data['section'], data['passoutYear'], file_path)
#     )
#     db.commit() 
#     return jsonify({"message": "Student added!"})

# # Upload classroom photo
# @app.route("/upload", methods=["POST"])
# def upload_classroom():
#     file = request.files['image']
#     file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
#     file.save(file_path)

#     results = recognition.recognize_faces(file_path)
#     return jsonify({"results": results})

# # Export Excel
# @app.route("/export", methods=["GET"])
# def export_excel():
#     file_path = attendance_export.export_to_excel()
#     return send_file(file_path, as_attachment=True)

# if __name__ == "__main__":
#     app.run(debug=True)
