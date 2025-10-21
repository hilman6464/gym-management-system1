from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from ..utils.db import get_db_connection
from ..utils.date_utils import to_jalali
from persiantools.jdatetime import JalaliDate
from datetime import datetime, timedelta

members_bp = Blueprint('members', __name__, url_prefix='/members')

# کمربندها
BELTS = ['سفید', 'زرد', 'سبز', 'آبی', 'قرمز',
         'پوم 1', 'پوم 2', 'پوم 3', 'پوم 4',
         'دان 1', 'دان 2', 'دان 3', 'دان 4', 'دان 5']

# ---------------- لیست اعضا ----------------
@members_bp.route('/')
def members():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM clubs")
    clubs = c.fetchall()

    club_filter = request.args.get('club_id')
    session_filter = request.args.get('session_id')
    search_query = request.args.get('search')

    # گرفتن سانس‌های باشگاه انتخاب شده (برای فیلتر)
    sessions = []
    if club_filter:
        c.execute('''
            SELECT s.session_id, s.class_time, s.coach_name 
            FROM sessions s 
            WHERE s.club_id = ? 
            ORDER BY s.class_time
        ''', (club_filter,))
        sessions = c.fetchall()

    query = '''SELECT m.*, 
                      c.name AS club_name, 
                      s.class_time, 
                      s.coach_name,
                      s.day_type,
                      s.days_display
               FROM members m
               LEFT JOIN sessions s ON m.session_id = s.session_id
               LEFT JOIN clubs c ON s.club_id = c.club_id'''
    params = []
    conditions = []

    if club_filter and club_filter != "":
        conditions.append("s.club_id=?")
        params.append(club_filter)

    if session_filter and session_filter != "":
        conditions.append("m.session_id=?")
        params.append(session_filter)

    if search_query and search_query.strip() != "":
        like_value = f"%{search_query}%"
        conditions.append("(m.name LIKE ? OR m.family_name LIKE ? OR m.national_id LIKE ? OR m.phone LIKE ?)")
        params.extend([like_value, like_value, like_value, like_value])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY c.name, s.class_time, m.family_name, m.name"

    c.execute(query, params)
    members_list = c.fetchall()
    conn.close()

    members_list_jalali = []
    today = datetime.now().date()
    
    for m in members_list:
        member_dict = dict(m)
        
        # تبدیل تاریخ‌ها به شمسی
        member_dict['birth_date_jalali'] = to_jalali(m['birth_date'])
        member_dict['insurance_date_jalali'] = to_jalali(m['insurance_date'])
        member_dict['belt_date_jalali'] = to_jalali(m['belt_date'])
        
        # محاسبه وضعیت بیمه
        member_dict['insurance_status'] = 'valid'
        if member_dict['insurance_date']:
            insurance_end = datetime.strptime(member_dict['insurance_date'], '%Y-%m-%d').date() + timedelta(days=365)
            if insurance_end < today:
                member_dict['insurance_status'] = 'expired'
            elif insurance_end <= today + timedelta(days=10):
                member_dict['insurance_status'] = 'soon'
        
        # سیستم هشدار ساده
        member_dict['alerts'] = get_simple_alerts(member_dict)
        
        members_list_jalali.append(member_dict)

    return render_template('members.html',
                           members=members_list_jalali,
                           clubs=clubs,
                           sessions=sessions,
                           club_filter=club_filter,
                           session_filter=session_filter,
                           search_query=search_query)

def get_simple_alerts(member_data):
    """سیستم هشدار ساده و بدون خطا"""
    alerts = []
    
    # هشدار بیمه
    insurance_alert = check_insurance_simple(member_data.get('insurance_date'))
    if insurance_alert:
        alerts.append(insurance_alert)
    
    # هشدار تولد
    birthday_alert = check_birthday_simple(member_data.get('birth_date'))
    if birthday_alert:
        alerts.append(birthday_alert)
    
    # هشدار کمربند
    belt_alert = check_belt_simple(member_data.get('belt'), member_data.get('belt_date'))
    if belt_alert:
        alerts.append(belt_alert)
    
    # 🆕 هشدار پرداخت
    if member_data.get('id'):  # فقط اگر عضو ID داره
        payment_alert = check_payment_simple(member_data['id'])
        if payment_alert:
            alerts.append(payment_alert)
    
    return alerts

def check_insurance_simple(insurance_date):
    """بررسی ساده بیمه"""
    if not insurance_date:
        return None
    
    try:
        insurance_dt = datetime.strptime(insurance_date, '%Y-%m-%d')
        expiry_date = insurance_dt + timedelta(days=365)
        today = datetime.now()
        days_left = (expiry_date - today).days
        
        if days_left <= 0:
            return {
                'type': 'insurance_expired',
                'message': '⚠️ بیمه منقضی شده',
                'css_class': 'insurance-expired'
            }
        elif days_left <= 10:
            return {
                'type': 'insurance_urgent',
                'message': f'🏥 {days_left} روز تا انقضای بیمه',
                'css_class': 'insurance-urgent'
            }
    except:
        pass
    
    return None

def check_birthday_simple(birth_date):
    """بررسی ساده تولد"""
    if not birth_date:
        return None
    
    try:
        birth_dt = datetime.strptime(birth_date, '%Y-%m-%d')
        today = datetime.now()
        
        # تولد امسال
        birthday_this_year = datetime(today.year, birth_dt.month, birth_dt.day)
        if birthday_this_year < today:
            birthday_this_year = datetime(today.year + 1, birth_dt.month, birth_dt.day)
        
        days_left = (birthday_this_year - today).days
        
        if 0 < days_left <= 5:
            return {
                'type': 'birthday',
                'message': f'🎂 {days_left} روز تا تولد',
                'css_class': 'birthday-alert'
            }
    except:
        pass
    
    return None

def check_belt_simple(current_belt, belt_date):
    """بررسی ساده کمربند - نسخه کامل بهبود یافته"""
    if not current_belt or not belt_date:
        return None
    
    belt_rules = {
        'سفید': 2, 'زرد': 3, 'سبز': 4, 'آبی': 6, 'قرمز': 9,
        'پوم 1': 12, 'پوم 2': 24, 'پوم 3': 36,
        'دان 1': 12, 'دان 2': 24, 'دان 3': 36, 'دان 4': 48
    }
    
    if current_belt not in belt_rules:
        return None
    
    try:
        belt_dt = datetime.strptime(belt_date, '%Y-%m-%d')
        upgrade_date = belt_dt + timedelta(days=belt_rules[current_belt] * 30)
        today = datetime.now()
        days_diff = (upgrade_date - today).days
        
        next_belt = get_next_belt(current_belt)
        
        # هشدار برای موارد گذشته
        if days_diff <= 0:
            days_passed = abs(days_diff)
            if days_passed > 30:
                months_passed = days_passed // 30
                return {
                    'type': 'belt_expired',
                    'message': f'⏰ {months_passed} ماه از موعد {next_belt} گذشته',
                    'css_class': 'belt-expired'
                }
            else:
                return {
                    'type': 'belt_upgrade', 
                    'message': f'🥋 {days_passed} روز از موعد {next_belt} گذشته',
                    'css_class': 'belt-alert'
                }
        
        # هشدار برای آینده (15 روز قبل)
        elif 0 < days_diff <= 15:
            return {
                'type': 'belt_upgrade',
                'message': f'🥋 {days_diff} روز تا {next_belt}',
                'css_class': 'belt-alert'
            }
                
    except Exception as e:
        print(f"خطا در بررسی کمربند: {e}")
    
    return None

def check_payment_simple(member_id):
    """بررسی وضعیت پرداخت شهریه - شبیه هشدار بیمه"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # پیدا کردن آخرین پرداخت
        c.execute('''
            SELECT year, month, payment_date 
            FROM payments 
            WHERE member_id = ? 
            ORDER BY year DESC, month DESC 
            LIMIT 1
        ''', (member_id,))
        
        last_payment = c.fetchone()
        conn.close()
        
        if not last_payment:
            return {
                'type': 'payment_missing',
                'message': '💰 هیچ پرداختی ثبت نشده',
                'css_class': 'payment-missing'
            }
        
        # تاریخ امروز به شمسی
        today_jalali = JalaliDate.today()
        current_year = today_jalali.year
        current_month = today_jalali.month
        
        # آخرین پرداخت انجام شده
        last_payment_year = last_payment['year']
        last_payment_month = last_payment['month']
        
        # محاسبه ماه‌های معوق
        overdue_months = 0
        year = last_payment_year
        month = last_payment_month + 1
        
        while year < current_year or (year == current_year and month <= current_month):
            # بررسی آیا برای این ماه پرداخت شده؟
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                SELECT payment_id FROM payments 
                WHERE member_id = ? AND year = ? AND month = ?
            ''', (member_id, year, month))
            has_payment = c.fetchone()
            conn.close()
            
            if not has_payment:
                overdue_months += 1
            
            month += 1
            if month > 12:
                month = 1
                year += 1
        
        if overdue_months > 0:
            # معوقه داره
            return {
                'type': 'payment_overdue',
                'message': f'💸 {overdue_months} ماه معوقه',
                'css_class': 'payment-overdue blink-red'
            }
        
        # اگر معوقه نداره، هشدار برای ماه آینده
        next_month = current_month + 1
        next_year = current_year
        if next_month > 12:
            next_month = 1
            next_year += 1
        
        # تاریخ شروع هشدار (15ام ماه جاری)
        reminder_start = JalaliDate(current_year, current_month, 15)
        
        if today_jalali >= reminder_start:
            days_until_deadline = (JalaliDate(next_year, next_month, 1) - today_jalali).days
            return {
                'type': 'payment_reminder', 
                'message': f'💰 {days_until_deadline} روز تا پرداخت',
                'css_class': 'payment-reminder'
            }
        
    except Exception as e:
        print(f"خطا در بررسی پرداخت: {e}")
    
    return None

def get_next_belt(current_belt):
    """دریافت کمربند بعدی"""
    belt_sequence = {
        'سفید': 'زرد', 'زرد': 'سبز', 'سبز': 'آبی', 'آبی': 'قرمز',
        'قرمز': 'پوم 1', 'پوم 1': 'پوم 2', 'پوم 2': 'پوم 3', 'پوم 3': 'پوم 4',
        'دان 1': 'دان 2', 'دان 2': 'دان 3', 'دان 3': 'دان 4', 'دان 4': 'دان 5'
    }
    return belt_sequence.get(current_belt, 'کمربند بعدی')

# ---------------- افزودن عضو ----------------
@members_bp.route('/add', methods=['GET', 'POST'])
def add_member():
    conn = get_db_connection()
    c = conn.cursor()
    
    # گرفتن لیست باشگاه‌ها
    c.execute("SELECT * FROM clubs ORDER BY name")
    clubs = c.fetchall()
    
    sessions = []
    if not clubs:
        # اگر باشگاهی وجود ندارد
        conn.close()
        return render_template('add_member.html', clubs=[], sessions=[], belts=BELTS, no_clubs=True)
    
    # اگر باشگاهی وجود دارد، سانس‌های اولین باشگاه رو بگیر
    first_club_id = clubs[0]['club_id']
    c.execute('''
        SELECT s.*, c.name as club_name 
        FROM sessions s 
        JOIN clubs c ON s.club_id = c.club_id 
        WHERE s.club_id = ? 
        ORDER BY s.class_time
    ''', (first_club_id,))
    sessions = c.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        family_name = request.form['family_name']
        national_id = request.form['national_id']
        phone = request.form['phone']
        belt = request.form['belt']
        birth_date_input = request.form['birth_date']
        insurance_start_input = request.form['insurance_start']
        session_id = request.form['session_id']
        belt_date_input = request.form.get('belt_date', '')

        # اعتبارسنجی فیلدهای ضروری
        if not name or not family_name or not national_id or not session_id:
            flash('لطفاً فیلدهای ضروری را پر کنید.', 'error')
            return redirect(url_for('members.add_member'))

        try:
            parts = list(map(int, birth_date_input.split('/')))
            birth_date = str(JalaliDate(*parts).to_gregorian())
        except Exception:
            birth_date = None

        try:
            parts = list(map(int, insurance_start_input.split('/')))
            insurance_start = str(JalaliDate(*parts).to_gregorian())
        except Exception:
            insurance_start = None

        # تبدیل تاریخ کمربند به میلادی
        try:
            if belt_date_input:
                parts = list(map(int, belt_date_input.split('/')))
                belt_date = str(JalaliDate(*parts).to_gregorian())
            else:
                belt_date = None
        except Exception:
            belt_date = None

        try:
            # اضافه کردن عضو با session_id
            c.execute('''INSERT INTO members 
                         (name, family_name, national_id, phone, belt, birth_date, 
                          insurance_date, session_id, belt_date)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (name, family_name, national_id, phone, belt, birth_date, 
                       insurance_start, session_id, belt_date))
            conn.commit()
            flash('عضو با موفقیت اضافه شد.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'خطا در ثبت عضو: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('members.members'))

    conn.close()
    return render_template('add_member.html', clubs=clubs, sessions=sessions, belts=BELTS, no_clubs=False)

# ---------------- API برای دریافت سانس‌های یک باشگاه ----------------
@members_bp.route('/api/sessions/<int:club_id>')
def get_sessions_by_club(club_id):
    """دریافت سانس‌های یک باشگاه خاص"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT s.session_id, s.coach_name, s.day_type, s.class_time, s.days_display
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
            'day_type': session['day_type'],
            'class_time': session['class_time'],
            'days_display': session['days_display']
        })
    
    return jsonify(sessions_list)

# ---------------- ویرایش عضو ----------------
@members_bp.route('/edit/<int:member_id>', methods=['GET', 'POST'])
def edit_member(member_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    # گرفتن اطلاعات عضو به همراه باشگاه و سانس
    c.execute('''
        SELECT m.*, s.session_id, s.club_id, s.coach_name, s.class_time, c.name as club_name
        FROM members m 
        LEFT JOIN sessions s ON m.session_id = s.session_id 
        LEFT JOIN clubs c ON s.club_id = c.club_id
        WHERE m.id=?
    ''', (member_id,))
    member = c.fetchone()

    if not member:
        conn.close()
        flash('عضو مورد نظر یافت نشد.', 'error')
        return redirect(url_for('members.members'))

    # گرفتن لیست باشگاه‌ها و سانس‌ها
    c.execute("SELECT * FROM clubs ORDER BY name")
    clubs = c.fetchall()
    
    if not clubs:
        conn.close()
        return render_template('edit_member.html', member=dict(member), clubs=[], sessions=[], belts=BELTS, no_clubs=True)
    
    # سانس‌های باشگاه فعلی عضو
    current_club_id = member['club_id'] if member['club_id'] else clubs[0]['club_id']
    c.execute('''
        SELECT s.*, c.name as club_name 
        FROM sessions s 
        JOIN clubs c ON s.club_id = c.club_id 
        WHERE s.club_id = ? 
        ORDER BY s.class_time
    ''', (current_club_id,))
    sessions = c.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        family_name = request.form['family_name']
        national_id = request.form['national_id']
        phone = request.form['phone']
        belt = request.form['belt']
        birth_date_input = request.form['birth_date']
        insurance_start_input = request.form['insurance_start']
        session_id = request.form['session_id']
        belt_date_input = request.form.get('belt_date', '')

        # اعتبارسنجی فیلدهای ضروری
        if not name or not family_name or not national_id or not session_id:
            flash('لطفاً فیلدهای ضروری را پر کنید.', 'error')
            return redirect(url_for('members.edit_member', member_id=member_id))

        try:
            parts = list(map(int, birth_date_input.split('/')))
            birth_date = str(JalaliDate(*parts).to_gregorian())
        except Exception:
            birth_date = None

        try:
            parts = list(map(int, insurance_start_input.split('/')))
            insurance_start = str(JalaliDate(*parts).to_gregorian())
        except Exception:
            insurance_start = None

        # تبدیل تاریخ کمربند به میلادی
        try:
            if belt_date_input:
                parts = list(map(int, belt_date_input.split('/')))
                belt_date = str(JalaliDate(*parts).to_gregorian())
            else:
                belt_date = None
        except Exception:
            belt_date = None

        try:
            # آپدیت عضو با session_id
            c.execute('''UPDATE members SET
                         name=?, family_name=?, national_id=?, phone=?, belt=?,
                         birth_date=?, insurance_date=?, session_id=?, belt_date=?
                         WHERE id=?''',
                      (name, family_name, national_id, phone, belt,
                       birth_date, insurance_start, session_id, belt_date, member_id))
            conn.commit()
            flash('عضو با موفقیت ویرایش شد.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'خطا در ویرایش عضو: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('members.members'))

    # تبدیل اطلاعات عضو به دیکشنری
    member_dict = dict(member)
    member_dict['birth_date_jalali'] = to_jalali(member['birth_date'])
    member_dict['insurance_date_jalali'] = to_jalali(member['insurance_date'])
    member_dict['belt_date_jalali'] = to_jalali(member['belt_date'])
    member_dict['alerts'] = get_simple_alerts(member_dict)

    conn.close()
    return render_template('edit_member.html', 
                         member=member_dict, 
                         clubs=clubs, 
                         sessions=sessions, 
                         belts=BELTS, 
                         no_clubs=False)

# ---------------- حذف عضو ----------------
@members_bp.route('/delete/<int:member_id>')
def delete_member(member_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # گرفتن نام عضو قبل از حذف
        c.execute("SELECT name, family_name FROM members WHERE id=?", (member_id,))
        member = c.fetchone()
        
        if member:
            member_name = f"{member['name']} {member['family_name']}"
            c.execute("DELETE FROM members WHERE id=?", (member_id,))
            conn.commit()
            flash(f'عضو {member_name} با موفقیت حذف شد.', 'success')
        else:
            flash('عضو مورد نظر یافت نشد.', 'error')
            
    except Exception as e:
        conn.rollback()
        flash(f'خطا در حذف عضو: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('members.members'))
