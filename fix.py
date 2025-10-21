from datetime import datetime, timedelta

def test_alert_system():
    print("🧪 تست سیستم هشدار...")
    
    # تست داده‌های مختلف
    test_cases = [
        {
            'name': 'بیمه منقضی شده',
            'insurance_date': (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d'),
            'birth_date': (datetime.now() - timedelta(days=365*15)).strftime('%Y-%m-%d'),
            'belt': 'سفید',
            'belt_date': (datetime.now() - timedelta(days=50)).strftime('%Y-%m-%d')
        },
        {
            'name': 'بیمه نزدیک انقضا', 
            'insurance_date': (datetime.now() - timedelta(days=355)).strftime('%Y-%m-%d'),
            'birth_date': (datetime.now() - timedelta(days=365*12)).strftime('%Y-%m-%d'),
            'belt': 'زرد',
            'belt_date': (datetime.now() - timedelta(days=80)).strftime('%Y-%m-%d')
        }
    ]
    
    for test in test_cases:
        alerts = get_simple_alerts(test)
        print(f"\n📋 {test['name']}:")
        for alert in alerts:
            print(f"   🔔 {alert['message']}")

def get_simple_alerts(member_data):
    """همان تابع موجود در members.py"""
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
    
    return alerts

def check_insurance_simple(insurance_date):
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
    if not birth_date:
        return None
    
    try:
        birth_dt = datetime.strptime(birth_date, '%Y-%m-%d')
        today = datetime.now()
        
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
        days_left = (upgrade_date - today).days
        
        if 0 < days_left <= 15:
            next_belt = get_next_belt(current_belt)
            return {
                'type': 'belt_upgrade',
                'message': f'🥋 {days_left} روز تا {next_belt}',
                'css_class': 'belt-alert'
            }
    except:
        pass
    
    return None

def get_next_belt(current_belt):
    belt_sequence = {
        'سفید': 'زرد', 'زرد': 'سبز', 'سبز': 'آبی', 'آبی': 'قرمز',
        'قرمز': 'پوم 1', 'پوم 1': 'پوم 2', 'پوم 2': 'پوم 3', 'پوم 3': 'پوم 4',
        'دان 1': 'دان 2', 'دان 2': 'دان 3', 'دان 3': 'دان 4', 'دان 4': 'دان 5'
    }
    return belt_sequence.get(current_belt, 'کمربند بعدی')

if __name__ == '__main__':
    test_alert_system()
