from flask import Blueprint, render_template, request, jsonify, flash
from ..utils.db import get_db_connection
from ..utils.date_utils import to_jalali
from persiantools.jdatetime import JalaliDate
from datetime import datetime, timedelta

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

# ---------------- صفحه اصلی حضور و غیاب ----------------
@attendance_bp.route('/')
def attendance_main():
    """صفحه اصلی حضور و غیاب"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # گرفتن لیست باشگاه‌ها
    c.execute("SELECT * FROM clubs ORDER BY name")
    clubs = c.fetchall()
    
    # گرفتن تاریخ دقیق ایران
    today_jalali = JalaliDate.today()
    current_month = today_jalali.month
    current_year = today_jalali.year
    current_day = today_jalali.day
    
    conn.close()
    
    return render_template('attendance.html', 
                         clubs=clubs,
                         current_month=current_month,
                         current_year=current_year,
                         current_day=current_day)

# ---------------- سیستم هشدار برای حضور و غیاب ----------------
def get_simple_alerts(member_data):
    """سیستم هشدار ساده - همانند members.py"""
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
    """بررسی ساده بیمه - انقضای ۱ ساله"""
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
    belt_sequence = {
        'سفید': 'زرد', 'زرد': 'سبز', 'سبز': 'آبی', 'آبی': 'قرمز',
        'قرمز': 'پوم 1', 'پوم 1': 'پوم 2', 'پوم 2': 'پوم 3', 'پوم 3': 'پوم 4',
        'دان 1': 'دان 2', 'دان 2': 'دان 3', 'دان 3': 'دان 4', 'دان 4': 'دان 5'
    }
    return belt_sequence.get(current_belt, 'کمربند بعدی')

# ---------------- API برای دریافت سانس‌های یک باشگاه ----------------
@attendance_bp.route('/api/attendance-sessions/<int:club_id>')
def get_sessions_by_club_attendance(club_id):
    """دریافت سانس‌های یک باشگاه خاص برای حضور و غیاب"""
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

# ---------------- API برای دریافت اعضای یک سانس ----------------
@attendance_bp.route('/api/attendance-members/<int:session_id>')
def get_members_by_session_attendance(session_id):
    """دریافت اعضای یک سانس خاص با اطلاعات کامل برای هشدارها"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # گرفتن اطلاعات کامل اعضا برای هشدارها
    c.execute('''
        SELECT m.id, m.name, m.family_name, m.national_id, 
               m.birth_date, m.insurance_date, m.belt, m.belt_date
        FROM members m 
        WHERE m.session_id = ? 
        ORDER BY m.family_name, m.name
    ''', (session_id,))
    members = c.fetchall()
    conn.close()
    
    members_list = []
    for member in members:
        member_dict = {
            'id': member['id'],
            'name': member['name'],
            'family_name': member['family_name'],
            'national_id': member['national_id'],
            'birth_date': member['birth_date'],
            'insurance_date': member['insurance_date'],
            'belt': member['belt'],
            'belt_date': member['belt_date']
        }
        
        # اضافه کردن هشدارها
        member_dict['alerts'] = get_simple_alerts(member_dict)
        
        members_list.append(member_dict)
    
    return jsonify(members_list)

# ---------------- API برای محاسبه تاریخ‌های مجاز ----------------
@attendance_bp.route('/api/calculate-dates/<int:session_id>')
def calculate_dates(session_id):
    """محاسبه تاریخ‌های مجاز یک سانس"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # دریافت اطلاعات سانس
    c.execute('''
        SELECT s.day_type, s.days_display
        FROM sessions s WHERE s.session_id = ?
    ''', (session_id,))
    
    session = c.fetchone()
    if not session:
        return jsonify({'error': 'سانس یافت نشد'}), 404
    
    # دریافت ماه و سال از پارامترها
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    if not month or not year:
        # استفاده از تاریخ جاری
        today_jalali = JalaliDate.today()
        month = today_jalali.month
        year = today_jalali.year
    
    # محاسبه تاریخ‌های مجاز
    dates = calculate_allowed_dates(session['day_type'], month, year)
    
    conn.close()
    return jsonify({
        'dates': dates,
        'month': month,
        'year': year,
        'day_type': session['day_type'],
        'session_id': session_id
    })

# ---------------- API برای ذخیره وضعیت حضور و غیاب ----------------
@attendance_bp.route('/api/save-attendance', methods=['POST'])
def save_attendance():
    """ذخیره وضعیت حضور و غیاب"""
    data = request.json
    member_id = data.get('member_id')
    date = data.get('date')
    status = data.get('status')
    session_id = data.get('session_id')
    
    if not all([member_id, date, status, session_id]):
        return jsonify({'success': False, 'error': 'داده‌های ناقص ارسال شده'}), 400
    
    if status not in ['present', 'absent', 'suspended']:
        return jsonify({'success': False, 'error': 'وضعیت نامعتبر'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # بررسی وجود رکورد قبلی
        c.execute('''SELECT id, status FROM attendance 
                     WHERE member_id=? AND attendance_date=? AND session_id=?''',
                  (member_id, date, session_id))
        existing = c.fetchone()
        
        if existing:
            # آپدیت رکورد موجود
            c.execute('''UPDATE attendance SET status=?, updated_at=CURRENT_TIMESTAMP
                         WHERE member_id=? AND attendance_date=? AND session_id=?''',
                      (status, member_id, date, session_id))
            action = 'updated'
        else:
            # درج رکورد جدید
            c.execute('''INSERT INTO attendance (member_id, session_id, attendance_date, status)
                         VALUES (?, ?, ?, ?)''',
                      (member_id, session_id, date, status))
            action = 'created'
        
        conn.commit()
        
        # گرفتن نام عضو برای پیام
        c.execute("SELECT name, family_name FROM members WHERE id=?", (member_id,))
        member = c.fetchone()
        
        if member:
            member_name = f"{member['name']} {member['family_name']}"
        else:
            member_name = "عضو"
        
        return jsonify({
            'success': True, 
            'message': f'وضعیت حضور {member_name} برای تاریخ {date} ذخیره شد',
            'action': action
        })
    
    except Exception as e:
        conn.rollback()
        print(f"❌ خطا در ذخیره حضور و غیاب: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        conn.close()

# ---------------- API برای دریافت وضعیت‌های ذخیره شده ----------------
@attendance_bp.route('/api/get-attendance')
def get_attendance_for_date():
    """دریافت وضعیت حضور برای یک سانس و تاریخ خاص"""
    session_id = request.args.get('session_id', type=int)
    date = request.args.get('date')
    
    if not session_id or not date:
        return jsonify({'success': False, 'error': 'پارامترهای session_id و date الزامی هستند'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT a.member_id, a.status, m.name, m.family_name
            FROM attendance a
            JOIN members m ON a.member_id = m.id
            WHERE a.session_id = ? AND a.attendance_date = ?
        ''', (session_id, date))
        
        attendance_data = c.fetchall()
        
        # تبدیل به دیکشنری برای دسترسی آسان
        result = {}
        for row in attendance_data:
            result[row['member_id']] = {
                'status': row['status'],
                'name': f"{row['name']} {row['family_name']}"
            }
        
        return jsonify({'success': True, 'data': result})
    
    except Exception as e:
        print(f"❌ خطا در دریافت حضور و غیاب: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        conn.close()

# ---------------- API برای تعلیق عضو ----------------
@attendance_bp.route('/api/suspend-member', methods=['POST'])
def suspend_member():
    """تعلیق یک عضو و تغییر تمام وضعیت‌هایش به معلق"""
    data = request.json
    member_id = data.get('member_id')
    session_id = data.get('session_id')
    
    if not member_id or not session_id:
        return jsonify({'success': False, 'error': 'پارامترهای member_id و session_id الزامی هستند'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # پیدا کردن تمام تاریخ‌های آینده این سانس
        today_jalali = JalaliDate.today()
        today_str = f"{today_jalali.year}/{today_jalali.month:02d}/{today_jalali.day:02d}"
        
        # تغییر تمام وضعیت‌های آینده به معلق
        c.execute('''
            UPDATE attendance SET status = 'suspended', updated_at = CURRENT_TIMESTAMP
            WHERE member_id = ? AND session_id = ? AND attendance_date >= ?
        ''', (member_id, session_id, today_str))
        
        updated_count = c.rowcount
        conn.commit()
        
        # گرفتن نام عضو
        c.execute("SELECT name, family_name FROM members WHERE id=?", (member_id,))
        member = c.fetchone()
        member_name = f"{member['name']} {member['family_name']}" if member else "عضو"
        
        return jsonify({
            'success': True, 
            'message': f'عضو {member_name} با موفقیت تعلیق شد ({updated_count} وضعیت به معلق تغییر کرد)',
            'updated_count': updated_count
        })
    
    except Exception as e:
        conn.rollback()
        print(f"❌ خطا در تعلیق عضو: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        conn.close()

# ---------------- API برای فعال‌سازی عضو ----------------
@attendance_bp.route('/api/activate-member', methods=['POST'])
def activate_member():
    """فعال‌سازی یک عضو تعلیق شده"""
    data = request.json
    member_id = data.get('member_id')
    session_id = data.get('session_id')
    
    if not member_id or not session_id:
        return jsonify({'success': False, 'error': 'پارامترهای member_id و session_id الزامی هستند'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # فقط وضعیت‌های معلق آینده رو به وضعیت عادی برگردون
        today_jalali = JalaliDate.today()
        today_str = f"{today_jalali.year}/{today_jalali.month:02d}/{today_jalali.day:02d}"
        
        # وضعیت‌های معلق آینده رو به 'absent' تغییر بده
        c.execute('''
            UPDATE attendance 
            SET status = 'absent', updated_at = CURRENT_TIMESTAMP
            WHERE member_id = ? AND session_id = ? AND attendance_date >= ? AND status = 'suspended'
        ''', (member_id, session_id, today_str))
        
        updated_count = c.rowcount
        conn.commit()
        
        # گرفتن نام عضو
        c.execute("SELECT name, family_name FROM members WHERE id=?", (member_id,))
        member = c.fetchone()
        member_name = f"{member['name']} {member['family_name']}" if member else "عضو"
        
        return jsonify({
            'success': True, 
            'message': f'عضو {member_name} با موفقیت فعال شد ({updated_count} وضعیت معلق به غایب تغییر کرد)',
            'updated_count': updated_count
        })
    
    except Exception as e:
        conn.rollback()
        print(f"❌ خطا در فعال‌سازی عضو: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        conn.close()

# ---------------- API برای دریافت اطلاعات یک سانس خاص ----------------
@attendance_bp.route('/api/session-details/<int:session_id>')
def get_session_details(session_id):
    """دریافت اطلاعات کامل یک سانس"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT s.session_id, s.coach_name, s.day_type, s.class_time, s.days_display,
               c.name as club_name, c.club_id
        FROM sessions s 
        JOIN clubs c ON s.club_id = c.club_id
        WHERE s.session_id = ?
    ''', (session_id,))
    
    session = c.fetchone()
    conn.close()
    
    if session:
        session_info = {
            'session_id': session['session_id'],
            'coach_name': session['coach_name'],
            'day_type': session['day_type'],
            'class_time': session['class_time'],
            'days_display': session['days_display'],
            'club_name': session['club_name'],
            'club_id': session['club_id']
        }
        return jsonify(session_info)
    else:
        return jsonify({'error': 'سانس یافت نشد'}), 404

# ---------------- توابع کمکی ----------------
def calculate_allowed_dates(day_type, month, year):
    """محاسبه تاریخ‌های مجاز بر اساس نوع سانس - نسخه تصحیح شده"""
    dates = []
    day_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']
    
    # محاسبه تعداد روزهای ماه
    try:
        if month <= 6:
            last_day = 31
        elif month <= 11:
            last_day = 30
        else:
            jalali_year = JalaliDate(year, 12, 1)
            last_day = 30 if jalali_year.is_leap() else 29
    except:
        last_day = 30
    
    for day in range(1, last_day + 1):
        try:
            jalali_date = JalaliDate(year, month, day)
            day_of_week = jalali_date.weekday()
            
            include_day = False
            
            if day_type == 'even':
                include_day = (day_of_week in [0, 2, 4])  # شنبه، دوشنبه، چهارشنبه
            elif day_type == 'odd':
                include_day = (day_of_week in [1, 3, 5])  # یکشنبه، سه‌شنبه، پنجشنبه
            elif day_type == 'weekend':
                include_day = (day_of_week in [5, 6])     # 🔥 تصحیح شده: پنجشنبه، جمعه
            
            if include_day:
                dates.append({
                    'date': f"{year}/{month:02d}/{day:02d}",
                    'day': day,
                    'day_name': day_names[day_of_week],
                    'full_display': f"{year}/{month:02d}/{day:02d}<br><span class='text-xs text-gray-500'>{day_names[day_of_week]}</span>"
                })
                
        except Exception as e:
            print(f"خطا در محاسبه تاریخ {year}/{month}/{day}: {e}")
            continue
    
    return dates

def get_month_name(month):
    """دریافت نام فارسی ماه"""
    month_names = {
        1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد',
        4: 'تیر', 5: 'مرداد', 6: 'شهریور', 
        7: 'مهر', 8: 'آبان', 9: 'آذر',
        10: 'دی', 11: 'بهمن', 12: 'اسفند'
    }
    return month_names.get(month, '')

def get_day_type_name(day_type):
    """دریافت نام فارسی نوع روز"""
    type_names = {
        'even': 'روزهای زوج',
        'odd': 'روزهای فرد', 
        'weekend': 'آخر هفته'
    }
    return type_names.get(day_type, 'همه روزها')
