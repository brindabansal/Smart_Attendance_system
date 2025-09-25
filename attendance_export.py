# attendance_export.py
import pandas as pd
from db import get_connection
from io import BytesIO

def export_attendance_to_excel():
    conn = get_connection()
    query = """
    SELECT a.attendance_id, s.name, s.roll_no AS roll, s.branch, s.section, a.date, a.status
    FROM attendance a
    JOIN students s ON a.student_id = s.student_id
    """
    df = pd.read_sql(query, conn)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    conn.close()
    return output




# import pandas as pd
# from db import cursor
# import os

# def export_to_excel():
#     cursor.execute("SELECT * FROM attendance")
#     rows = cursor.fetchall()
#     df = pd.DataFrame(rows)
#     file_path = "attendance_export.xlsx"
#     df.to_excel(file_path, index=False)
#     return file_path
