import schedule
import time
from threading import Thread
from .backup_utils import BackupManager

def auto_backup_job():
    """وظیفه بک‌آپ خودکار"""
    manager = BackupManager()
    success, message = manager.create_backup('auto')
    print(f"بک‌آپ خودکار: {message}")

def run_scheduler():
    """اجرای زمان‌بند بک‌آپ خودکار"""
    # زمان‌بندی بک‌آپ روزانه ساعت 4 صبح
    schedule.every().day.at("04:00").do(auto_backup_job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # بررسی هر دقیقه

def start_auto_backup():
    """شروع بک‌آپ خودکار در تابع جداگانه"""
    backup_thread = Thread(target=run_scheduler, daemon=True)
    backup_thread.start()
