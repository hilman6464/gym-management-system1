# app/__init__.py
from flask import Flask, render_template
import os
from .utils.db import init_db, get_db_connection
import threading
import time
from datetime import datetime
import shutil
from pathlib import Path

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)

    # ایجاد تمام جداول در context برنامه
    with app.app_context():
        init_db()  # حالا این فقط جداول رو اگر وجود ندارن ایجاد میکنه

    # ثبت Blueprint ها
    from .routes.members import members_bp
    from .routes.clubs import clubs_bp
    from .routes.sessions import sessions_bp
    from .routes.reports import reports_bp
    from .routes.payments import payments_bp
    from .routes.age_categories import age_categories_bp
    from .routes.attendance import attendance_bp
    
    # ثبت Blueprint بک‌آپ (به صورت شرطی)
    try:
        from .routes.backup import backup_bp
        app.register_blueprint(backup_bp)
        print("✅ سیستم بک‌آپ فعال شد")
    except ImportError as e:
        print(f"⚠️ ماژول بک‌آپ یافت نشد - سیستم بک‌آپ غیرفعال: {e}")

    # ثبت تمام Blueprint ها
    app.register_blueprint(members_bp)
    app.register_blueprint(clubs_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(age_categories_bp)
    app.register_blueprint(attendance_bp)

    @app.route('/')
    def index():
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM members")
        total_members = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM clubs")
        total_clubs = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = c.fetchone()[0]
        conn.close()
        return render_template('index.html', 
                             total_members=total_members, 
                             total_clubs=total_clubs,
                             total_sessions=total_sessions)

    # شروع بک‌آپ خودکار در تابع جداگانه
    start_auto_backup()
    
    return app

def auto_backup_job():
    """وظیفه بک‌آپ خودکار"""
    try:
        from .routes.backup import BackupManager
        manager = BackupManager()
        success, message = manager.create_backup('auto')
        
        if success:
            print(f"✅ بک‌آپ خودکار موفق: {message}")
        else:
            print(f"❌ بک‌آپ خودکار ناموفق: {message}")
            
    except ImportError:
        print("⚠️ ماژول BackupManager یافت نشد - بک‌آپ خودکار غیرفعال")
    except Exception as e:
        print(f"❌ خطا در بک‌آپ خودکار: {e}")


def run_scheduler():
    """اجرای زمان‌بند بک‌آپ خودکار"""
    print("🎯 سیستم بک‌آپ خودکار راه‌اندازی شد")
    print("⏰ بک‌آپ خودکار هر روز ساعت 4 صبح اجرا می‌شود")
    
    # تست اولیه سیستم بک‌آپ
    print("🧪 اجرای تست اولیه بک‌آپ...")
    try:
        auto_backup_job()
        print("✅ تست اولیه بک‌آپ تکمیل شد")
    except Exception as e:
        print(f"⚠️ تست اولیه بک‌آپ با خطا مواجه شد: {e}")
    
    last_log_time = None
    last_backup_day = None
    
    while True:
        try:
            now = datetime.now()
            current_time = f"{now.hour:02d}:{now.minute:02d}"
            current_day = now.day
            
            # لاگ زمان فعلی (هر 60 دقیقه)
            if last_log_time != current_time and now.minute == 0:
                print(f"🕒 زمان‌سنج فعال - زمان فعلی: {current_time}")
                last_log_time = current_time
            
            # 🎯 **حالت تولید واقعی: فقط ساعت 4 صبح**
            if now.hour == 4 and now.minute == 0:
                # جلوگیری از اجرای مکرر در همان روز
                if last_backup_day != current_day:
                    print(f"🎯 ساعت 4 صبح! اجرای بک‌آپ خودکار... ({current_time})")
                    auto_backup_job()
                    last_backup_day = current_day
                    print("✅ بک‌آپ خودکار اجرا شد")
                else:
                    print("⏭️ بک‌آپ امروز قبلاً اجرا شده است")
                
                # خواب به مدت 61 ثانیه برای جلوگیری از اجرای مکرر
                time.sleep(61)
            else:
                # خواب 30 ثانیه‌ای بین بررسی‌ها
                time.sleep(30)
                
        except KeyboardInterrupt:
            print("🛑 سیستم بک‌آپ خودکار متوقف شد")
            break
        except Exception as e:
            print(f"❌ خطا در زمان‌بند بک‌آپ: {e}")
            time.sleep(60)  # در صورت خطا 1 دقیقه صبر کن

def start_auto_backup():
    """شروع بک‌آپ خودکار در تابع جداگانه"""
    try:
        backup_thread = threading.Thread(target=run_scheduler, daemon=True)
        backup_thread.start()
        print("✅ سیستم بک‌آپ خودکار در پس‌زمینه راه‌اندازی شد")
    except Exception as e:
        print(f"⚠️ خطا در راه‌اندازی بک‌آپ خودکار: {e}")

# برای تست مستقیم
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
