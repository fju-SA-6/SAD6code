import mysql.connector

# ==========================================
# 全局資料庫連線設定
# ==========================================
db_config = {
    'host': '127.0.0.1',
    'port': 3306,              
    'user': 'root',
    'password': '' # ⚠️ 請在這裡換成你的 MySQL 密碼
}

def get_db_connection():
    """
    建立並回傳共用的 MySQL 資料庫連線與游標，
    若不存在 graduation_db 則會先建立。
    """
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("CREATE DATABASE IF NOT EXISTS graduation_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE graduation_db")
        
        return conn, cursor
    except mysql.connector.Error as err:
        print(f"❌ 資料庫連線失敗: {err}")
        return None, None
