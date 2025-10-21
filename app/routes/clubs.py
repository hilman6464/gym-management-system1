from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..utils.db import get_db_connection
from persiantools.jdatetime import JalaliDate

clubs_bp = Blueprint('clubs', __name__, url_prefix='/clubs')

@clubs_bp.route('/')
def clubs():
    conn = get_db_connection()
    c = conn.cursor()
    
    # تعداد سانس‌های هر باشگاه
    c.execute('''
        SELECT c.*, COUNT(s.session_id) as session_count 
        FROM clubs c 
        LEFT JOIN sessions s ON c.club_id = s.club_id 
        GROUP BY c.club_id 
        ORDER BY c.name
    ''')
    clubs_list = c.fetchall()
    conn.close()

    return render_template('clubs.html', clubs=clubs_list)

@clubs_bp.route('/add', methods=['GET', 'POST'])
def add_club():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        
        if not name:
            flash('لطفاً نام باشگاه را وارد کنید.', 'error')
            return redirect(url_for('clubs.add_club'))

        created_date = str(JalaliDate.today())

        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute('''INSERT INTO clubs (name, address, phone, created_date)
                         VALUES (?, ?, ?, ?)''',
                      (name, address, phone, created_date))
            conn.commit()
            flash('باشگاه با موفقیت اضافه شد.', 'success')
        except Exception as e:
            flash(f'خطا در ثبت باشگاه: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('clubs.clubs'))

    return render_template('add_club.html')

@clubs_bp.route('/edit/<int:club_id>', methods=['GET', 'POST'])
def edit_club(club_id):
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')

        if not name:
            flash('لطفاً نام باشگاه را وارد کنید.', 'error')
            return redirect(url_for('clubs.edit_club', club_id=club_id))

        try:
            c.execute('''UPDATE clubs SET 
                         name=?, address=?, phone=?
                         WHERE club_id=?''',
                      (name, address, phone, club_id))
            conn.commit()
            flash('باشگاه با موفقیت ویرایش شد.', 'success')
        except Exception as e:
            flash(f'خطا در ویرایش باشگاه: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('clubs.clubs'))

    c.execute("SELECT * FROM clubs WHERE club_id=?", (club_id,))
    club = c.fetchone()
    conn.close()

    if not club:
        flash('باشگاه مورد نظر یافت نشد.', 'error')
        return redirect(url_for('clubs.clubs'))

    return render_template('edit_club.html', club=dict(club))

@clubs_bp.route('/delete/<int:club_id>')
def delete_club(club_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # بررسی آیا سانسی به این باشگاه وابسته است؟
        c.execute("SELECT COUNT(*) FROM sessions WHERE club_id=?", (club_id,))
        session_count = c.fetchone()[0]
        
        if session_count > 0:
            flash('امکان حذف باشگاه وجود ندارد زیرا سانس‌هایی به آن وابسته هستند.', 'error')
        else:
            c.execute("DELETE FROM clubs WHERE club_id=?", (club_id,))
            conn.commit()
            flash('باشگاه با موفقیت حذف شد.', 'success')
    except Exception as e:
        flash(f'خطا در حذف باشگاه: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('clubs.clubs'))

@clubs_bp.route('/<int:club_id>/sessions')
def club_sessions(club_id):
    """نمایش سانس‌های یک باشگاه خاص"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # اطلاعات باشگاه
    c.execute("SELECT * FROM clubs WHERE club_id=?", (club_id,))
    club = c.fetchone()
    
    if not club:
        flash('باشگاه مورد نظر یافت نشد.', 'error')
        return redirect(url_for('clubs.clubs'))
    
    # سانس‌های این باشگاه
    c.execute('''
        SELECT s.*, 
               CASE 
                   WHEN s.day_type = 'even' THEN 'زوج'
                   WHEN s.day_type = 'odd' THEN 'فرد' 
                   WHEN s.day_type = 'weekend' THEN 'آخر هفته'
                   ELSE ''
               END as day_type_name,
               COUNT(m.id) as member_count
        FROM sessions s 
        LEFT JOIN members m ON s.session_id = m.session_id
        WHERE s.club_id = ?
        GROUP BY s.session_id
        ORDER BY s.class_time
    ''', (club_id,))
    sessions = c.fetchall()
    
    conn.close()
    
    return render_template('club_sessions.html', club=dict(club), sessions=sessions)
