# app/routes/backup.py
from flask import Blueprint, render_template, request, jsonify, flash, send_file
from ..utils.backup_utils import BackupManager
from pathlib import Path

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

@backup_bp.route('/')
def backup_management():
    """صفحه مدیریت بک‌آپ"""
    manager = BackupManager()
    backups = manager.get_backup_list()
    
    return render_template('backup_management.html', 
                         backups=backups,
                         total_count=len(backups),
                         auto_count=len([b for b in backups if b['type'] == 'auto']),
                         manual_count=len([b for b in backups if b['type'] == 'manual']))

@backup_bp.route('/create_manual', methods=['POST'])
def create_manual_backup():
    """ایجاد بک‌آپ دستی"""
    manager = BackupManager()
    success, message = manager.create_backup('manual')
    
    if success:
        flash(f'✅ {message}', 'success')
    else:
        flash(f'❌ {message}', 'error')
    
    return jsonify({'success': success, 'message': message})

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
            return send_file(backup_path, as_attachment=True)
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
        flash(f'❌ خطا در حذف بک‌آپ: {str(e)}', 'error')
        return jsonify({'success': False})
