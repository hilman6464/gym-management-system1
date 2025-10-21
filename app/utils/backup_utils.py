# app/utils/backup_utils.py
import os
import shutil
from datetime import datetime
from pathlib import Path
import sqlite3
from ..utils.db import DB_NAME

class BackupManager:
    def __init__(self):
        self.backup_dir = Path(__file__).parent.parent / 'backups'
        self.auto_dir = self.backup_dir / 'auto'
        self.manual_dir = self.backup_dir / 'manual'
        self.logs_dir = self.backup_dir / 'logs'
        
        # ایجاد پوشه‌ها اگر وجود ندارند
        self._create_directories()
    
    def _create_directories(self):
        """ایجاد پوشه‌های لازم برای بک‌آپ"""
        for directory in [self.backup_dir, self.auto_dir, self.manual_dir, self.logs_dir]:
            directory.mkdir(exist_ok=True)
    
    def _get_backup_filename(self, backup_type='manual'):
        """تولید نام فایل بک‌آپ بر اساس تاریخ و ساعت"""
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        if backup_type == 'auto':
            return f"auto_backup_{timestamp}.db"
        else:
            return f"manual_backup_{timestamp}.db"
    
    def _log_backup(self, message, level='INFO'):
        """ثبت لاگ بک‌آپ"""
        log_file = self.logs_dir / 'backup.log'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def create_backup(self, backup_type='manual'):
        """ایجاد بک‌آپ از دیتابیس"""
        try:
            # بررسی وجود فایل دیتابیس اصلی
            if not DB_NAME.exists():
                self._log_backup(f"فایل دیتابیس اصلی یافت نشد: {DB_NAME}", 'ERROR')
                return False, "فایل دیتابیس اصلی یافت نشد"
            
            # تعیین مسیر مقصد
            if backup_type == 'auto':
                dest_dir = self.auto_dir
                filename = self._get_backup_filename('auto')
            else:
                dest_dir = self.manual_dir
                filename = self._get_backup_filename('manual')
            
            backup_path = dest_dir / filename
            
            # ایجاد کپی از دیتابیس
            shutil.copy2(DB_NAME, backup_path)
            
            # ثبت لاگ
            file_size = backup_path.stat().st_size
            log_message = f"بک‌آپ {backup_type} ایجاد شد: {filename} ({file_size} بایت)"
            self._log_backup(log_message)
            
            # پاک‌سازی بک‌آپ‌های قدیمی (نگهداری فقط ۷ روز اخیر)
            self._cleanup_old_backups()
            
            return True, f"بک‌آپ با موفقیت ایجاد شد: {filename}"
            
        except Exception as e:
            error_msg = f"خطا در ایجاد بک‌آپ: {str(e)}"
            self._log_backup(error_msg, 'ERROR')
            return False, error_msg
    
    def _cleanup_old_backups(self, days_to_keep=7):
        """پاک‌سازی بک‌آپ‌های قدیمی"""
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            for backup_type in ['auto', 'manual']:
                if backup_type == 'auto':
                    backup_files = self.auto_dir.glob('*.db')
                else:
                    backup_files = self.manual_dir.glob('*.db')
                
                for backup_file in backup_files:
                    if backup_file.stat().st_mtime < cutoff_time:
                        backup_file.unlink()
                        self._log_backup(f"بک‌آپ قدیمی حذف شد: {backup_file.name}")
                        
        except Exception as e:
            self._log_backup(f"خطا در پاک‌سازی بک‌آپ‌های قدیمی: {str(e)}", 'ERROR')
    
    def get_backup_list(self, backup_type='all'):
        """دریافت لیست بک‌آپ‌ها"""
        backups = []
        
        if backup_type in ['all', 'auto']:
            for backup_file in self.auto_dir.glob('*.db'):
                stat = backup_file.stat()
                backups.append({
                    'type': 'auto',
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'size_human': self._human_readable_size(stat.st_size)
                })
        
        if backup_type in ['all', 'manual']:
            for backup_file in self.manual_dir.glob('*.db'):
                stat = backup_file.stat()
                backups.append({
                    'type': 'manual',
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'size_human': self._human_readable_size(stat.st_size)
                })
        
        # مرتب‌سازی بر اساس تاریخ (جدیدترین اول)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups
    
    def _human_readable_size(self, size_bytes):
        """تبدیل حجم به فرمت قابل خواندن"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def restore_backup(self, backup_path):
        """بازگردانی دیتابیس از بک‌آپ"""
        try:
            # بررسی وجود فایل بک‌آپ
            if not Path(backup_path).exists():
                return False, "فایل بک‌آپ یافت نشد"
            
            # ایجاد بک‌آپ از وضعیت فعلی قبل از بازگردانی
            self.create_backup('manual')
            
            # جایگزینی دیتابیس فعلی با بک‌آپ
            shutil.copy2(backup_path, DB_NAME)
            
            self._log_backup(f"دیتابیس از بک‌آپ بازگردانی شد: {Path(backup_path).name}")
            return True, "بازگردانی با موفقیت انجام شد"
            
        except Exception as e:
            error_msg = f"خطا در بازگردانی بک‌آپ: {str(e)}"
            self._log_backup(error_msg, 'ERROR')
            return False, error_msg
