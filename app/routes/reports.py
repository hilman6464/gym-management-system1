# app/routes/reports.py
from flask import Blueprint, render_template, request, jsonify
from ..utils.db import get_db_connection
from ..utils.date_utils import to_jalali
from persiantools.jdatetime import JalaliDate
from datetime import datetime, timedelta

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

# ---------------- گزارش پیشرفته اعضا ----------------
@reports_bp.route('/advanced')
def advanced_report():
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # گرفتن لیست باشگاه‌ها
        c.execute("SELECT * FROM clubs ORDER BY name")
        clubs = c.fetchall()

        # گرفتن لیست سانس‌ها
        c.execute('''
            SELECT s.session_id, s.coach_name, s.class_time, s.club_id, c.name as club_name
            FROM sessions s 
            JOIN clubs c ON s.club_id = c.club_id
            ORDER BY c.name, s.class_time
        ''')
        sessions = c.fetchall()

        # لیست کمربندها
        belts = ['سفید', 'زرد', 'سبز', 'آبی', 'قرمز',
                 'پوم 1', 'پوم 2', 'پوم 3', 'پوم 4',
                 'دان 1', 'دان 2', 'دان 3', 'دان 4', 'دان 5']

        # گرفتن فیلترها
        club_filter = request.args.get('club_id', '')
        session_filter = request.args.get('session_id', '')
        belt_filter = request.args.get('belt', '')
        insurance_filter = request.args.get('insurance', '')

        # ساخت کوئری پایه
        query = """
            SELECT 
                m.*, 
                s.coach_name AS session_name,
                s.session_id,
                c.name AS club_name,
                c.club_id
            FROM members m 
            LEFT JOIN sessions s ON m.session_id = s.session_id
            LEFT JOIN clubs c ON s.club_id = c.club_id
            WHERE 1=1
        """
        params = []
        conditions = []

        # فیلتر باشگاه
        if club_filter:
            conditions.append("c.club_id = ?")
            params.append(club_filter)
        
        # فیلتر سانس
        if session_filter:
            conditions.append("m.session_id = ?")
            params.append(session_filter)
        
        # فیلتر کمربند
        if belt_filter:
            conditions.append("m.belt = ?")
            params.append(belt_filter)

        # فیلتر بیمه
        today = datetime.now().date()
        if insurance_filter == 'expired':
            conditions.append("(m.insurance_date IS NOT NULL AND DATE(m.insurance_date, '+365 days') < ?)")
            params.append(today)
        elif insurance_filter == '10days':
            target_date = today + timedelta(days=10)
            conditions.append("(m.insurance_date IS NOT NULL AND DATE(m.insurance_date, '+365 days') BETWEEN ? AND ?)")
            params.extend([today, target_date])

        # اضافه کردن شرایط به کوئری
        if conditions:
            query += " AND " + " AND ".join(conditions)

        # اجرای کوئری
        c.execute(query, params)
        members_list = c.fetchall()

        # پردازش داده‌ها
        members_list_jalali = []
        for m in members_list:
            member_dict = dict(m)
            
            # تبدیل تاریخ‌ها به شمسی
            member_dict['birth_date_jalali'] = to_jalali(member_dict['birth_date'])
            member_dict['insurance_date_jalali'] = to_jalali(member_dict['insurance_date'])
            
            # محاسبه وضعیت بیمه
            member_dict['insurance_status'] = 'valid'
            if member_dict['insurance_date']:
                try:
                    insurance_date = datetime.strptime(member_dict['insurance_date'], '%Y-%m-%d').date()
                    expiry_date = insurance_date + timedelta(days=365)
                    
                    if expiry_date < today:
                        member_dict['insurance_status'] = 'expired'
                    elif expiry_date <= today + timedelta(days=10):
                        member_dict['insurance_status'] = 'soon'
                except Exception as e:
                    print(f"خطا در محاسبه بیمه برای عضو {member_dict['id']}: {e}")
                    member_dict['insurance_status'] = 'unknown'
            
            members_list_jalali.append(member_dict)

        conn.close()
        
        return render_template('advanced_report.html',
                               members=members_list_jalali,
                               clubs=clubs,
                               sessions=sessions,
                               belts=belts,
                               club_filter=club_filter,
                               session_filter=session_filter,
                               belt_filter=belt_filter,
                               insurance_filter=insurance_filter)
    
    except Exception as e:
        print(f"❌ خطا در گزارش پیشرفته: {e}")
        if conn:
            conn.close()
        return render_template('advanced_report.html',
                               members=[],
                               clubs=[],
                               sessions=[],
                               belts=[],
                               club_filter=club_filter,
                               session_filter=session_filter,
                               belt_filter=belt_filter,
                               insurance_filter=insurance_filter,
                               error=str(e))

# ---------------- API برای دریافت سانس‌های یک باشگاه ----------------
@reports_bp.route('/api/sessions/<int:club_id>')
def get_sessions_by_club(club_id):
    """دریافت سانس‌های یک باشگاه خاص برای فیلتر"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT s.session_id, s.coach_name, s.class_time
            FROM sessions s 
            WHERE s.club_id = ? 
            ORDER BY s.class_time
        ''', (club_id,))
        
        sessions = c.fetchall()
        conn.close()
        
        sessions_list = []
        for session in sessions:
            sessions_list.append({
                'session_id': session['session_id'],
                'coach_name': session['coach_name'],
                'class_time': session['class_time']
            })
        
        return jsonify(sessions_list)
        
    except Exception as e:
        print(f"❌ خطا در دریافت سانس‌ها: {e}")
        return jsonify([])
