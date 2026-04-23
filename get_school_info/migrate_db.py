import mysql.connector

db_config = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': ''
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("USE graduation_db")
    
    # Check if semester column exists
    cursor.execute("SHOW COLUMNS FROM FJU_GenEd_Departments LIKE 'semester'")
    if not cursor.fetchone():
        print("Adding semester column...")
        cursor.execute("ALTER TABLE FJU_GenEd_Departments ADD COLUMN semester VARCHAR(20) NOT NULL DEFAULT '下學期' AFTER id")
        # Drop old unique index
        cursor.execute("ALTER TABLE FJU_GenEd_Departments DROP INDEX course_name")
        # Add new unique index
        cursor.execute("ALTER TABLE FJU_GenEd_Departments ADD UNIQUE INDEX unique_course_sem (semester, course_name)")
        conn.commit()
        print("Migration successful.")
    else:
        print("Semester column already exists.")
        
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
