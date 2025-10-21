# app/routes/sessions.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..utils.db import get_db_connection
from persiantools.jdatetime import JalaliDate

sessions_bp = Blueprint('sessions', __name__, url_prefix='/sessions')

# تعریف انواع روزها
DAY_TYPES = {
    'even': {'name': 'زوج', 'days': 'شنبه، دوشنبه، چهارشنبه'},
    'odd': {'name': 'فرد', 'days': 'یکشنبه، سه‌شنبه، پنجشنبه'},
    'weekend': {'name': 'آخر هفته', 'days': 'پنجشنبه، جمعه'}
}

def get_days_display(day_type):
    """دریافت نمایش روزها بر اساس نوع"""
    day_displays = {
        'even': 'شنبه، دوشنبه، چهارشنبه',
        'odd': 'یکشنبه، سه‌شنبه، پنجشنبه',
        'weekend': 'پنجشنبه، جمعه'
    }
    return day_displays.get(day_type, '')

@sessions_bp.route('/add/<int:club_id>', methods=['GET', 'POST'])
def add_session(club_id):
    """افزودن سانس جدید به باشگاه"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # اطلاعات باشگاه
    c.execute("SELECT * FROM clubs WHERE club_id=?", (club_id,))
    club = c.fetchone()
    
    if not club:
        flash('باشگاه مورد نظر یافت نشد.', 'error')
        conn.close()
        return redirect(url_for('clubs.clubs'))

    if request.method == 'POST':
        coach_name = request.form['coach_name']
        day_type = request.form['day_type']
        class_time = request.form['class_time']
        
        if not coach_name or not day_type or not class_time:
            flash('لطفاً تمام فیلدهای ضروری را پر کنید.', 'error')
            conn.close()
            return redirect(url_for('sessions.add_session', club_id=club_id))

        # محاسبه خودکار روزهای نمایش
        days_display = get_days_display(day_type)
        created_date = str(JalaliDate.today())

        try:
            c.execute('''INSERT INTO sessions (club_id, coach_name, day_type, days_display, class_time, created_date)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (club_id, coach_name, day_type, days_display, class_time, created_date))
            conn.commit()
            flash('سانس با موفقیت اضافه شد.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'خطا در ثبت سانس: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('clubs.club_sessions', club_id=club_id))

    conn.close()
    return render_template('add_session.html', club=dict(club), day_types=DAY_TYPES)

@sessions_bp.route('/edit/<int:session_id>', methods=['GET', 'POST'])
def edit_session(session_id):
    """ویرایش سانس"""
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        coach_name = request.form['coach_name']
        day_type = request.form['day_type']
        class_time = request.form['class_time']

        if not coach_name or not day_type or not class_time:
            flash('لطفاً تمام فیلدهای ضروری را پر کنید.', 'error')
            conn.close()
            return redirect(url_for('sessions.edit_session', session_id=session_id))

        # محاسبه خودکار روزهای نمایش
        days_display = get_days_display(day_type)

        try:
            c.execute('''UPDATE sessions SET 
                         coach_name=?, day_type=?, days_display=?, class_time=?
                         WHERE session_id=?''',
                      (coach_name, day_type, days_display, class_time, session_id))
            conn.commit()
            flash('سانس با موفقیت ویرایش شد.', 'success')
            
            # یافتن club_id برای redirect
            c.execute("SELECT club_id FROM sessions WHERE session_id=?", (session_id,))
            session_data = c.fetchone()
            club_id = session_data['club_id'] if session_data else None
            
        except Exception as e:
            flash(f'خطا در ویرایش سانس: {str(e)}', 'error')
        finally:
            conn.close()

        if club_id:
            return redirect(url_for('clubs.club_sessions', club_id=club_id))
        else:
            return redirect(url_for('clubs.clubs'))

    # GET request - نمایش فرم ویرایش
    c.execute("SELECT s.*, c.name as club_name FROM sessions s JOIN clubs c ON s.club_id = c.club_id WHERE s.session_id=?", (session_id,))
    session = c.fetchone()
    conn.close()

    if not session:
        flash('سانس مورد نظر یافت نشد.', 'error')
        return redirect(url_for('clubs.clubs'))

    return render_template('edit_session.html', session=dict(session), day_types=DAY_TYPES)

@sessions_bp.route('/delete/<int:session_id>')
def delete_session(session_id):
    """حذف سانس"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # یافتن club_id قبل از حذف
        c.execute("SELECT club_id FROM sessions WHERE session_id=?", (session_id,))
        session_data = c.fetchone()
        club_id = session_data['club_id'] if session_data else None
        
        # بررسی آیا عضوی به این سانس وابسته است؟
        c.execute("SELECT COUNT(*) FROM members WHERE session_id=?", (session_id,))
        member_count = c.fetchone()[0]
        
        if member_count > 0:
            flash('امکان حذف سانس وجود ندارد زیرا اعضایی به آن وابسته هستند.', 'error')
        else:
            c.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
            conn.commit()
            flash('سانس با موفقیت حذف شد.', 'success')
    except Exception as e:
        flash(f'خطا در حذف سانس: {str(e)}', 'error')
    finally:
        conn.close()

    if club_id:
        return redirect(url_for('clubs.club_sessions', club_id=club_id))
    else:
        return redirect(url_for('clubs.clubs'))
