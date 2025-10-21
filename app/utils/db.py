import sqlite3
import os
from pathlib import Path

# مسیر مطلق برای دیتابیس
BASE_DIR = Path(__file__).parent.parent
DB_NAME = BASE_DIR / 'gym.db'

print(f"🎯 مسیر دیتابیس: {DB_NAME}")

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """ایجاد جداول فقط اگر وجود ندارن"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # ایجاد جدول clubs اگر وجود نداره
    c.execute('''
        CREATE TABLE IF NOT EXISTS clubs (
            club_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            created_date TEXT
        )
    ''')
    
    # ایجاد جدول sessions اگر وجود نداره
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER NOT NULL,
            coach_name TEXT NOT NULL,
            day_type TEXT NOT NULL,
            days_display TEXT NOT NULL,
            class_time TEXT NOT NULL,
            created_date TEXT,
            FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE
        )
    ''')
    
    # ایجاد جدول members اگر وجود نداره
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            family_name TEXT NOT NULL,
            national_id TEXT NOT NULL,
            phone TEXT,
            belt TEXT,
            birth_date TEXT,
            insurance_date TEXT,
            belt_date TEXT,
            session_id INTEGER,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE SET NULL
        )
    ''')
    
    # ایجاد جدول payments اگر وجود نداره
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            payment_date TEXT,
            month INTEGER,
            year INTEGER,
            tracking_code TEXT,  -- 🆕 ستون جدید برای کد پیگیری
            status TEXT DEFAULT 'paid',
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    ''')
    
    # 🆕 اضافه کردن ستون tracking_code اگر وجود ندارد
    try:
        c.execute("ALTER TABLE payments ADD COLUMN tracking_code TEXT")
        print("✅ ستون tracking_code به جدول payments اضافه شد")
    except sqlite3.OperationalError:
        print("ℹ️ ستون tracking_code از قبل وجود دارد")
    
    # ایجاد جدول attendance اگر وجود نداره
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id),
            UNIQUE(member_id, attendance_date, session_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ تمام جداول بررسی/ایجاد شدند")

def init_payments_table():
    """برای سازگاری"""
    pass

# وقتی این فایل اجرا میشه، فقط جداول رو بررسی کن
if __name__ == '__main__':
    init_db()
