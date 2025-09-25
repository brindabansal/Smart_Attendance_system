import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json

# ==========================
# DB CONNECTION
# ==========================
def get_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            database='smartattendance',
            user='root',
            password='vrinda487'
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error: {e}")
        return None


# ==========================
# ADMIN FUNCTION: Manage students
# ==========================
def save_student(name, roll_no, role="admin", branch=None, section=None, year=None, passout_year=None,photo_path=None):
    if role != "admin":
        print("Unauthorized: only admin can save/update students")
        return None

    conn = get_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor(dictionary=True)

        # Check if student exists
        cursor.execute(" SELECT student_id FROM students WHERE roll_no = %s", (roll_no,))
        result = cursor.fetchone()

        if result:
            student_id = result['student_id']
            cursor.execute(
                """UPDATE students SET name=%s, branch=%s, section=%s, year=%s, passout_year=%s ,photo_path=%s
                   WHERE student_id=%s""",
                (name, branch, section, year, passout_year,photo_path, student_id)
            )
        else:
            cursor.execute(
                """INSERT INTO students (name, roll_no, branch, section, year, passout_year,photo_path)
                   VALUES (%s, %s, %s, %s, %s, %s,%s)""",
                (name, roll_no, branch, section, year, passout_year,photo_path)
            )
            student_id = cursor.lastrowid

        conn.commit()
        return student_id
    finally:
        if conn:
            cursor.close()
            conn.close()



# ==========================
# TEACHER FUNCTION: Save attendance
# ==========================
def save_attendance(student_id, recorded_by, recognized=True, role="teacher"):
    if role != "teacher":
        print("Unauthorized: only teacher can save attendance")
        return

    conn = get_connection()
    if conn is None:
        return
    try:
        cursor = conn.cursor()
        date_today = datetime.now().strftime("%Y-%m-%d")
        status = "Present" if recognized else "Absent"
        cursor.execute(
            "INSERT INTO attendance (student_id, date, status, recorded_by) VALUES (%s, %s, %s, %s)",
            (student_id, date_today, status, recorded_by)
        )
        conn.commit()
    finally:
        if conn:
            cursor.close()
            conn.close()








# import mysql.connector
# from mysql.connector import Error

# def get_connection():
#     try:
#         conn = mysql.connector.connect(
#             host='localhost',
#             database='smart_attendance',
#             user='root',
#             password='YOUR_ROOT_PASSWORD'
#         )
#         if conn.is_connected():
#             print("Connected to MySQL")
#             return conn
#     except Error as e:
#         print(f"Error: {e}")
#         return None
    








# import mysql.connector
# from dotenv import load_dotenv
# import os

# load_dotenv()

# db = mysql.connector.connect(
#     host=os.getenv("DB_HOST"),
#     user=os.getenv("DB_USER"),
#     password=os.getenv("DB_PASSWORD"),
#     database=os.getenv("DB_NAME")
# )

# cursor = db.cursor(dictionary=True)
