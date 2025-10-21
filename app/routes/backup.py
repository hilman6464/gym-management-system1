
from flask import Blueprint, render_template, request, jsonify, flash, send_file, redirect, url_for
import os
import shutil
from datetime import datetime
from pathlib import Path
from ..utils.db import DB_NAME

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

class BackupManager:
    def __init__(self):
        self.backup_dir = Path(__file__).parent.parent.parent / 'backups'
        self.auto_dir = self.backup_dir / 'auto'
        self.manual_dir = self.backup_dir / 'manual'
        self.logs_dir = self.backup_dir / 'logs'
        
        # ایجاد پوشه‌ها اگر وجود ندارند
        self._create_directories()
    
    def _create_directories(self):
        """ایجاد پوشه‌های لازم برای بک‌آپ"""
        for directory in [self.backup_dir, self.auto_dir, self.manual_dir, self.logs_dir]:
            directory.mkdir(exist_ok=True)
        print(f"📁 پوشه‌های بک‌آپ در: {self.backup_dir}")
    
    def _get_backup_filename(self, backup_type='manual'):
        """تولید نام فایل بک‌آپ بر اساس تاریخ و ساعت"""
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        if backup_type == 'auto':
            return f"auto_backup_{timestamp}.db"
        else:
            return f"manual_backup_{timestamp}.db"
    
    def _log_backup(self, message, level='INFO'):
        """ثبت لاگ بک‌آپ"""
        try:
            log_file = self.logs_dir / 'backup.log'
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] [{level}] {message}\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"❌ خطا در ثبت لاگ: {e}")
    
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
            deleted_count = 0
            
            for backup_type in ['auto', 'manual']:
                if backup_type == 'auto':
                    backup_files = list(self.auto_dir.glob('*.db'))
                else:
                    backup_files = list(self.manual_dir.glob('*.db'))
                
                for backup_file in backup_files:
                    if backup_file.stat().st_mtime < cutoff_time:
                        backup_file.unlink()
                        self._log_backup(f"بک‌آپ قدیمی حذف شد: {backup_file.name}")
                        deleted_count += 1
            
            if deleted_count > 0:
                print(f"🗑️ {deleted_count} فایل بک‌آپ قدیمی حذف شد")
                        
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

@backup_bp.route('/')
def backup_management():
    """صفحه مدیریت بک‌آپ"""
    try:
        manager = BackupManager()
        backups = manager.get_backup_list()
        
        return render_template('backup_management.html', 
                             backups=backups,
                             total_count=len(backups),
                             auto_count=len([b for b in backups if b['type'] == 'auto']),
                             manual_count=len([b for b in backups if b['type'] == 'manual']))
    except Exception as e:
        flash(f'خطا در بارگذاری صفحه بک‌آپ: {str(e)}', 'error')
        return render_template('backup_management.html', 
                             backups=[],
                             total_count=0,
                             auto_count=0,
                             manual_count=0)

@backup_bp.route('/create_manual', methods=['POST'])
def create_manual_backup():
    """ایجاد بک‌آپ دستی"""
    try:
        manager = BackupManager()
        success, message = manager.create_backup('manual')
        
        if success:
            flash(f'✅ {message}', 'success')
        else:
            flash(f'❌ {message}', 'error')
        
        return jsonify({'success': success, 'message': message})
    
    except Exception as e:
        error_msg = f'خطا در ایجاد بک‌آپ دستی: {str(e)}'
        flash(f'❌ {error_msg}', 'error')
        return jsonify({'success': False, 'message': error_msg})

@backup_bp.route('/download/<path:filename>')
def download_backup(filename):
    """دانلود فایل بک‌آپ"""
    try:
        manager = BackupManager()
        backup_path = None
        
        # پیدا کردن مسیر فایل
        for backup in manager.get_backup_list('all'):
            if backup['filename'] == filename:
                backup_path = backup['path']
                break
        
        if backup_path and Path(backup_path).exists():
            return send_file(backup_path, as_attachment=True, download_name=filename)
        else:
            flash('فایل بک‌آپ یافت نشد', 'error')
            return redirect(url_for('backup.backup_management'))
            
    except Exception as e:
        flash(f'خطا در دانلود: {str(e)}', 'error')
        return redirect(url_for('backup.backup_management'))

@backup_bp.route('/delete/<path:filename>', methods=['POST'])
def delete_backup(filename):
    """حذف فایل بک‌آپ"""
    try:
        manager = BackupManager()
        
        # پیدا کردن و حذف فایل
        for backup in manager.get_backup_list('all'):
            if backup['filename'] == filename:
                Path(backup['path']).unlink()
                manager._log_backup(f"بک‌آپ حذف شد: {filename}")
                flash('✅ بک‌آپ با موفقیت حذف شد', 'success')
                return jsonify({'success': True})
        
        flash('❌ فایل بک‌آپ یافت نشد', 'error')
        return jsonify({'success': False})
        
    except Exception as e:
        error_msg = f'خطا در حذف بک‌آپ: {str(e)}'
        flash(f'❌ {error_msg}', 'error')
        return jsonify({'success': False, 'message': error_msg})

@backup_bp.route('/test_auto_backup')
def test_auto_backup():
    """تست بک‌آپ خودکار - فقط برای توسعه"""
    try:
        manager = BackupManager()
        success, message = manager.create_backup('auto')
        
        if success:
            flash(f'✅ تست بک‌آپ خودکار موفق: {message}', 'success')
        else:
            flash(f'❌ تست بک‌آپ خودکار ناموفق: {message}', 'error')
            
        return redirect(url_for('backup.backup_management'))
        
    except Exception as e:
        flash(f'❌ خطا در تست بک‌آپ: {str(e)}', 'error')
        return redirect(url_for('backup.backup_management'))
