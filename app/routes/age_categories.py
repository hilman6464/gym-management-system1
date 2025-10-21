from flask import Blueprint, render_template, request, jsonify
from ..utils.db import get_db_connection
from ..utils.date_utils import to_jalali
from persiantools.jdatetime import JalaliDate
from datetime import datetime

age_categories_bp = Blueprint('age_categories', __name__, url_prefix='/age_categories')

# تعریف رده‌های سنی تکواندو
AGE_CATEGORIES = {
    'خردسالان': (4, 11),      # 4-11 سال
    'نونهالان': (12, 14),     # 12-14 سال  
    'نوجوانان': (15, 17),     # 15-17 سال
    'جوانان': (18, 21),       # 18-21 سال
    'بزرگسالان': (22, 99)     # 22+ سال
}

def calculate_age_category(birth_date):
    """محاسبه رده سنی بر اساس تاریخ تولد"""
    if not birth_date:
        return None
    
    try:
        # تبدیل تاریخ تولد به datetime
        birth_date_obj = datetime.strptime(birth_date, '%Y-%m-%d').date()
        
        # محاسبه سن
        today = datetime.now().date()
        age = today.year - birth_date_obj.year - ((today.month, today.day) < (birth_date_obj.month, birth_date_obj.day))
        
        # پیدا کردن رده سنی
        for category, (min_age, max_age) in AGE_CATEGORIES.items():
            if min_age <= age <= max_age:
                return category
        
        return 'نامشخص'
    except Exception as e:
        print(f"خطا در محاسبه سن: {e}")
        return 'نامشخص'

def jalali_to_gregorian(jalali_date_str):
    """تبدیل تاریخ شمسی به میلادی"""
    if not jalali_date_str:
        return None
    try:
        parts = list(map(int, jalali_date_str.split('/')))
        if len(parts) != 3:
            return None
        jalali_date = JalaliDate(parts[0], parts[1], parts[2])
        return jalali_date.to_gregorian()
    except Exception as e:
        print(f"خطا در تبدیل تاریخ: {e}")
        return None

# ---------------- API برای دریافت سانس‌های یک باشگاه ----------------
@age_categories_bp.route('/api/sessions/<int:club_id>')
def get_sessions_by_club(club_id):
    """دریافت سانس‌های یک باشگاه خاص برای فیلتر"""
    try:
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
        
    except Exception as e:
        print(f"❌ خطا در دریافت سانس‌ها: {e}")
        return jsonify([])

# ---------------- گزارش رده‌های سنی ----------------
@age_categories_bp.route('/report')
def age_report():
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # ---------- گرفتن فیلترها ----------
        start_date_fa = request.args.get('start_date', '')  # تاریخ شمسی
        end_date_fa = request.args.get('end_date', '')      # تاریخ شمسی
        session_filter = request.args.get('session_id', '')
        club_filter = request.args.get('club_id', '')  # 🆕 فیلتر جدید باشگاه
        belt_filter = request.args.get('belt', '')
        age_category_filter = request.args.get('age_category', '')

        print(f"🔍 فیلترها: club={club_filter}, session={session_filter}, start_date={start_date_fa}, belt={belt_filter}")

        # ---------- گرفتن لیست باشگاه‌ها ----------
        c.execute("SELECT club_id, name FROM clubs ORDER BY name")
        clubs = c.fetchall()
        print(f"✅ تعداد باشگاه‌ها: {len(clubs)}")

        # ---------- گرفتن لیست سانس‌ها ----------
        c.execute('''
            SELECT s.session_id, s.coach_name, s.class_time, s.club_id, c.name as club_name
            FROM sessions s 
            JOIN clubs c ON s.club_id = c.club_id
            ORDER BY c.name, s.class_time
        ''')
        all_sessions = c.fetchall()
        print(f"✅ تعداد کل سانس‌ها: {len(all_sessions)}")

        belts = ['سفید', 'زرد', 'سبز', 'آبی', 'قرمز',
                 'پوم 1', 'پوم 2', 'پوم 3', 'پوم 4',
                 'دان 1', 'دان 2', 'دان 3', 'دان 4', 'دان 5']

        # ---------- کوئری اصلی ----------
        query = """
            SELECT 
                m.id,
                m.name,
                m.family_name,
                m.national_id,
                m.phone,
                m.belt,
                m.birth_date,
                s.coach_name AS session_name,
                s.session_id,
                c.name as club_name,
                c.club_id
            FROM members m
            LEFT JOIN sessions s ON m.session_id = s.session_id
            LEFT JOIN clubs c ON s.club_id = c.club_id
            WHERE 1=1
        """
        params = []

        # 🆕 فیلتر باشگاه
        if club_filter:
            query += " AND c.club_id = ?"
            params.append(club_filter)

        # فیلتر سانس
        if session_filter:
            query += " AND m.session_id = ?"
            params.append(session_filter)

        # فیلتر کمربند
        if belt_filter:
            query += " AND m.belt = ?"
            params.append(belt_filter)

        # فیلتر تاریخ شروع (شمسی)
        if start_date_fa:
            start_date_gregorian = jalali_to_gregorian(start_date_fa)
            if start_date_gregorian:
                query += " AND m.birth_date >= ?"
                params.append(str(start_date_gregorian))

        # فیلتر تاریخ پایان (شمسی)
        if end_date_fa:
            end_date_gregorian = jalali_to_gregorian(end_date_fa)
            if end_date_gregorian:
                query += " AND m.birth_date <= ?"
                params.append(str(end_date_gregorian))

        query += " ORDER BY m.family_name, m.name"

        print(f"📋 کوئری: {query}")
        print(f"📋 پارامترها: {params}")

        c.execute(query, params)
        members = c.fetchall()
        print(f"✅ تعداد اعضا: {len(members)}")

        # پردازش اعضا و محاسبه رده سنی
        members_list = []
        age_stats = {category: 0 for category in AGE_CATEGORIES.keys()}
        age_stats['نامشخص'] = 0

        for member in members:
            member_dict = dict(member)
            
            # محاسبه رده سنی
            age_category = calculate_age_category(member_dict['birth_date'])
            member_dict['age_category'] = age_category or 'نامشخص'
            
            # تبدیل تاریخ تولد به شمسی
            member_dict['birth_date_jalali'] = to_jalali(member_dict['birth_date'])
            
            # آمار رده‌های سنی
            if age_category in age_stats:
                age_stats[age_category] += 1
            else:
                age_stats['نامشخص'] += 1
            
            members_list.append(member_dict)

        # فیلتر بر اساس رده سنی
        if age_category_filter:
            if age_category_filter == 'نامشخص':
                members_list = [m for m in members_list if m['age_category'] == 'نامشخص']
            else:
                members_list = [m for m in members_list if m['age_category'] == age_category_filter]

        conn.close()

        return render_template('age_report.html',
                               members=members_list,
                               clubs=clubs,  # 🆕 ارسال لیست باشگاه‌ها
                               sessions=all_sessions,  # 🆕 ارسال همه سانس‌ها
                               belts=belts,
                               age_categories=list(AGE_CATEGORIES.keys()) + ['نامشخص'],
                               age_stats=age_stats,
                               start_date=start_date_fa,
                               end_date=end_date_fa,
                               club_filter=club_filter,  # 🆕 ارسال فیلتر باشگاه
                               session_filter=session_filter,
                               belt_filter=belt_filter,
                               age_category_filter=age_category_filter)
    
    except Exception as e:
        print(f"❌ خطای جدی در گزارش رده سنی: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        print(f"📋 جزئیات خطا:\n{error_details}")
        
        if conn:
            conn.close()
            
        return render_template('age_report.html',
                               members=[],
                               clubs=[],
                               sessions=[],
                               belts=[],
                               age_categories=list(AGE_CATEGORIES.keys()) + ['نامشخص'],
                               age_stats={},
                               start_date=start_date_fa,
                               end_date=end_date_fa,
                               club_filter=club_filter,
                               session_filter=session_filter,
                               belt_filter=belt_filter,
                               age_category_filter=age_category_filter,
                               error=f"خطا در بارگذاری داده‌ها: {str(e)}")

# ---------------- Route تست برای دیباگ ----------------
@age_categories_bp.route('/debug')
def debug_age_categories():
    return "✅ صفحه رده‌های سنی در دسترس است"
