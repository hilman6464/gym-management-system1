# app/routes/payments.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from ..utils.db import get_db_connection
from ..utils.date_utils import to_jalali
from persiantools.jdatetime import JalaliDate
from datetime import datetime

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

# ---------------- API برای دریافت سانس‌های یک باشگاه ----------------
@payments_bp.route('/api/sessions/<int:club_id>')
def get_sessions_by_club(club_id):
    """دریافت سانس‌های یک باشگاه خاص"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT s.session_id, s.coach_name, s.class_time, s.day_type, s.days_display
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
            'class_time': session['class_time'],
            'day_type': session['day_type'],
            'days_display': session['days_display']
        })
    
    return jsonify(sessions_list)

# ---------------- API برای بررسی کد پیگیری تکراری ----------------
@payments_bp.route('/check-tracking-code', methods=['POST'])
def check_tracking_code():
    """بررسی لحظه‌ای کد پیگیری تکراری"""
    data = request.json
    tracking_code = data.get('tracking_code', '').strip()
    
    if not tracking_code:
        return jsonify({'exists': False})
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''SELECT p.payment_id, p.payment_date, m.name, m.family_name 
                     FROM payments p
                     JOIN members m ON p.member_id = m.id
                     WHERE p.tracking_code = ?''', (tracking_code,))
        existing_tracking = c.fetchone()
        
        if existing_tracking:
            # تبدیل تاریخ به شمسی برای نمایش
            existing_date_jalali = to_jalali(existing_tracking['payment_date'])
            return jsonify({
                'exists': True,
                'existing_date': existing_date_jalali,
                'member_name': f"{existing_tracking['name']} {existing_tracking['family_name']}"
            })
        else:
            return jsonify({'exists': False})
            
    except Exception as e:
        return jsonify({'exists': False, 'error': str(e)})
    finally:
        conn.close()

# ---------------- ثبت پرداخت جدید ----------------
@payments_bp.route('/add', methods=['GET', 'POST'])
def add_payment():
    conn = get_db_connection()
    
    if request.method == 'GET':
        try:
            session_filter = request.args.get('session_filter', '')
            club_filter = request.args.get('club_filter', '')
            search_query = request.args.get('search', '')
            
            c = conn.cursor()
            c.execute("SELECT * FROM clubs")
            clubs = c.fetchall()
            
            c.execute("SELECT * FROM sessions")
            all_sessions = c.fetchall()
            
            filtered_sessions = all_sessions
            if club_filter:
                c.execute("SELECT * FROM sessions WHERE club_id = ?", (club_filter,))
                filtered_sessions = c.fetchall()
            
            query = """
                SELECT m.id, m.name, m.family_name, m.national_id, 
                       s.coach_name as session_name, s.session_id,
                       c.name as club_name, c.club_id
                FROM members m 
                LEFT JOIN sessions s ON m.session_id = s.session_id 
                LEFT JOIN clubs c ON s.club_id = c.club_id
                WHERE 1=1
            """
            params = []
            conditions = []

            if club_filter:
                query += " AND c.club_id = ?"
                params.append(club_filter)
                
            if session_filter:
                query += " AND m.session_id = ?"
                params.append(session_filter)
            
            if search_query:
                query += " AND (m.name LIKE ? OR m.family_name LIKE ? OR m.national_id LIKE ?)"
                like_val = f"%{search_query}%"
                params.extend([like_val, like_val, like_val])
            
            query += " ORDER BY c.name, s.coach_name, m.family_name, m.name"
            
            c.execute(query, params)
            filtered_members = c.fetchall()
            
            conn.close()
            
            return render_template('add_payment.html', 
                                filtered_members=filtered_members, 
                                sessions=filtered_sessions,
                                all_sessions=all_sessions,
                                clubs=clubs,
                                club_filter=club_filter,
                                session_filter=session_filter,
                                search_query=search_query)
            
        except Exception as e:
            flash(f'خطا در بارگذاری اطلاعات اعضا: {str(e)}', 'error')
            conn.close()
            return render_template('add_payment.html', filtered_members=[], sessions=[], all_sessions=[], clubs=[])
    
    if request.method == 'POST':
        try:
            member_id = request.form['member_id']
            amount = request.form['amount']
            payment_date_fa = request.form['payment_date']
            month = request.form['month']
            year = request.form['year']
            tracking_code = request.form.get('tracking_code', '').strip()
            
            if not member_id or not amount or not payment_date_fa or not month or not year:
                flash('لطفاً تمام فیلدهای ضروری را پر کنید.', 'error')
                return redirect(url_for('payments.add_payment'))
            
            c = conn.cursor()
            
            # 🔥 بررسی کد پیگیری تکراری
            if tracking_code:
                c.execute('''SELECT p.payment_id, p.payment_date, m.name, m.family_name 
                             FROM payments p
                             JOIN members m ON p.member_id = m.id
                             WHERE p.tracking_code = ?''', (tracking_code,))
                existing_tracking = c.fetchone()
                
                if existing_tracking:
                    # تبدیل تاریخ به شمسی برای نمایش
                    existing_date_jalali = to_jalali(existing_tracking['payment_date'])
                    flash(f'❌ این کد پیگیری قبلاً در تاریخ {existing_date_jalali} برای {existing_tracking["name"]} {existing_tracking["family_name"]} ثبت شده است.', 'error')
                    conn.close()
                    return redirect(url_for('payments.add_payment'))
            
            try:
                parts = list(map(int, payment_date_fa.split('/')))
                if len(parts) != 3:
                    raise ValueError("فرمت تاریخ نادرست است")
                
                payment_date_gregorian = str(JalaliDate(parts[0], parts[1], parts[2]).to_gregorian())
            except Exception as e:
                flash('خطا در تبدیل تاریخ. لطفاً تاریخ را به فرمت صحیح وارد کنید (مثال: 1404/07/01).', 'error')
                conn.close()
                return redirect(url_for('payments.add_payment'))
            
            # بررسی پرداخت تکراری برای همان عضو در همان ماه و سال
            c.execute('''SELECT payment_id FROM payments 
                         WHERE member_id = ? AND month = ? AND year = ?''', 
                      (member_id, month, year))
            existing_payment = c.fetchone()
            
            if existing_payment:
                flash('این عضو قبلاً برای این ماه و سال پرداخت خود را ثبت کرده است.', 'error')
                conn.close()
                return redirect(url_for('payments.add_payment'))
            
            # ثبت پرداخت جدید
            c.execute('''INSERT INTO payments (member_id, amount, payment_date, month, year, tracking_code, status) 
                         VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                      (member_id, amount, payment_date_gregorian, month, year, tracking_code, 'paid'))
            conn.commit()
            
            # گرفتن نام عضو برای پیام موفقیت
            c.execute("SELECT name, family_name FROM members WHERE id = ?", (member_id,))
            member = c.fetchone()
            member_name = f"{member['name']} {member['family_name']}" if member else "عضو"
            
            month_names = {
                '1': 'فروردین', '2': 'اردیبهشت', '3': 'خرداد',
                '4': 'تیر', '5': 'مرداد', '6': 'شهریور',
                '7': 'مهر', '8': 'آبان', '9': 'آذر',
                '10': 'دی', '11': 'بهمن', '12': 'اسفند'
            }
            month_name = month_names.get(month, month)
            
            if tracking_code:
                flash(f'✅ پرداخت برای {member_name} به مبلغ {amount} تومان برای ماه {month_name} سال {year} با کد پیگیری {tracking_code} ثبت شد.', 'success')
            else:
                flash(f'✅ پرداخت برای {member_name} به مبلغ {amount} تومان برای ماه {month_name} سال {year} ثبت شد.', 'success')
            
            return redirect(url_for('payments.add_payment'))
            
        except Exception as e:
            conn.rollback()
            flash(f'خطا در ثبت پرداخت: {str(e)}', 'error')
            return redirect(url_for('payments.add_payment'))
        finally:
            conn.close()

# ---------------- گزارش پرداخت‌ها ----------------
@payments_bp.route('/report')
def payments_report():
    conn = get_db_connection()
    c = conn.cursor()

    search_query = request.args.get('search', '').strip()
    session_filter = request.args.get('session_id', '')
    payment_status = request.args.get('status', '')
    month_filter = request.args.get('month', '')
    year_filter = request.args.get('year', '')

    c.execute("SELECT * FROM sessions")
    sessions = c.fetchall()

    query = """
        SELECT 
            m.id, 
            m.name, 
            m.family_name, 
            m.national_id, 
            m.phone, 
            s.coach_name AS session_name,
            p.amount, 
            p.payment_date,
            p.month,
            p.year,
            p.status,
            p.payment_id,
            p.tracking_code
        FROM members m
        LEFT JOIN sessions s ON m.session_id = s.session_id
        LEFT JOIN payments p ON m.id = p.member_id
    """
    params = []
    conditions = []

    if month_filter:
        conditions.append("p.month = ?")
        params.append(month_filter)
    
    if year_filter:
        conditions.append("p.year = ?")
        params.append(year_filter)

    if session_filter:
        conditions.append("m.session_id = ?")
        params.append(session_filter)
    
    if search_query:
        conditions.append("(m.name LIKE ? OR m.family_name LIKE ? OR m.national_id LIKE ?)")
        like_val = f"%{search_query}%"
        params.extend([like_val, like_val, like_val])
    
    if payment_status == "paid":
        conditions.append("p.payment_id IS NOT NULL")
    elif payment_status == "unpaid":
        conditions.append("p.payment_id IS NULL")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    else:
        query += " WHERE p.payment_id IS NOT NULL"
    
    query += " ORDER BY p.year DESC, p.month DESC, m.family_name, m.name"

    c.execute(query, params)
    members_list = []
    
    today_jalali = JalaliDate.today()
    current_year = today_jalali.year
    current_month = today_jalali.month
    
    for m in c.fetchall():
        m_dict = dict(m)
        
        if m_dict['payment_date']:
            m_dict['payment_date_jalali'] = to_jalali(m_dict['payment_date'])
        else:
            m_dict['payment_date_jalali'] = '-'
        
        if m_dict['payment_date']:
            payment_date = datetime.strptime(m_dict['payment_date'], '%Y-%m-%d').date()
            today = datetime.now().date()
            days_diff = (today - payment_date).days
            m_dict['days_overdue'] = max(0, days_diff - 5)
            m_dict['payment_status'] = 'paid'
        else:
            m_dict['days_overdue'] = None
            m_dict['payment_status'] = 'unpaid'
        
        member_id = m_dict['id']
        c2 = conn.cursor()
        
        c2.execute('''
            SELECT month, year FROM payments 
            WHERE member_id = ? 
            ORDER BY year DESC, month DESC 
            LIMIT 1
        ''', (member_id,))
        last_payment = c2.fetchone()
        
        if last_payment:
            last_month = last_payment['month']
            last_year = last_payment['year']
            
            overdue_months = []
            year = last_year
            month = last_month + 1
            
            while year < current_year or (year == current_year and month <= current_month):
                c2.execute('''
                    SELECT payment_id FROM payments 
                    WHERE member_id = ? AND month = ? AND year = ?
                ''', (member_id, month, year))
                has_payment = c2.fetchone()
                
                if not has_payment:
                    overdue_months.append({'month': month, 'year': year})
                
                month += 1
                if month > 12:
                    month = 1
                    year += 1
            
            overdue_count = len(overdue_months)
            if overdue_count > 0:
                last_overdue = overdue_months[-1]
                m_dict['overdue_count'] = overdue_count
                m_dict['last_overdue_month'] = last_overdue['month']
                m_dict['last_overdue_year'] = last_overdue['year']
                
                if overdue_count == 1:
                    m_dict['overdue_status'] = 'warning'
                else:
                    m_dict['overdue_status'] = 'danger'
            else:
                m_dict['overdue_count'] = 0
                m_dict['overdue_status'] = 'current'
        else:
            m_dict['overdue_count'] = current_month
            m_dict['overdue_status'] = 'danger'
            m_dict['last_overdue_month'] = current_month
            m_dict['last_overdue_year'] = current_year
        
        members_list.append(m_dict)

    conn.close()
    
    return render_template('payments_report.html',
                           members=members_list,
                           sessions=sessions,
                           session_filter=session_filter,
                           search_query=search_query,
                           payment_status=payment_status,
                           month=month_filter,
                           year=year_filter)

# ---------------- حذف پرداخت ----------------
@payments_bp.route('/delete/<int:payment_id>')
def delete_payment(payment_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT m.name, m.family_name, p.amount, p.month, p.year FROM payments p JOIN members m ON p.member_id = m.id WHERE p.payment_id=?", (payment_id,))
        payment_info = c.fetchone()
        
        c.execute("DELETE FROM payments WHERE payment_id=?", (payment_id,))
        conn.commit()
        conn.close()
        
        if payment_info:
            month_names = {
                '1': 'فروردین', '2': 'اردیبهشت', '3': 'خرداد',
                '4': 'تیر', '5': 'مرداد', '6': 'شهریور',
                '7': 'مهر', '8': 'آبان', '9': 'آذر',
                '10': 'دی', '11': 'بهمن', '12': 'اسفند'
            }
            month_name = month_names.get(str(payment_info['month']), payment_info['month'])
            flash(f'پرداخت {payment_info["amount"]} تومانی برای {payment_info["name"]} {payment_info["family_name"]} (ماه {month_name} سال {payment_info["year"]}) با موفقیت حذف شد.', 'success')
        else:
            flash('پرداخت با موفقیت حذف شد.', 'success')
            
    except Exception as e:
        flash(f'خطا در حذف پرداخت: {str(e)}', 'error')
    
    return redirect(url_for('payments.payments_report'))
