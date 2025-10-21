from datetime import datetime, timedelta
from persiantools.jdatetime import JalaliDate

class BeltCalculator:
    BELT_RULES = {
        'سفید': {'next': 'زرد', 'months': 2},
        'زرد': {'next': 'سبز', 'months': 3},
        'سبز': {'next': 'آبی', 'months': 4},
        'آبی': {'next': 'قرمز', 'months': 6},
        'قرمز': {'next': 'پوم 1', 'months': 9},
        'پوم 1': {'next': 'پوم 2', 'months': 12},
        'پوم 2': {'next': 'پوم 3', 'months': 24},
        'پوم 3': {'next': 'پوم 4', 'months': 36},
        'دان 1': {'next': 'دان 2', 'months': 12},
        'دان 2': {'next': 'دان 3', 'months': 24},
        'دان 3': {'next': 'دان 4', 'months': 36},
        'دان 4': {'next': 'دان 5', 'months': 48}
    }
    
    def get_belt_upgrade_alert(self, current_belt, belt_date):
        if not current_belt or not belt_date:
            return None
        
        if current_belt not in self.BELT_RULES:
            return None
        
        rule = self.BELT_RULES[current_belt]
        upgrade_date = self._calculate_upgrade_date(belt_date, rule['months'])
        days_left = self._days_until(upgrade_date)
        
        if 0 < days_left <= 15:
            return {
                'type': 'belt_upgrade',
                'message': f"{days_left} روز تا کمربند {rule['next']}",
                'days_left': days_left,
                'priority': 3,
                'css_class': 'belt-alert'
            }
        
        return None
    
    def _calculate_upgrade_date(self, belt_date, months):
        # تبدیل تاریخ و اضافه کردن ماه‌ها
        belt_dt = datetime.strptime(belt_date, '%Y-%m-%d')
        upgrade_dt = belt_dt + timedelta(days=months*30)  # تقریبی
        return upgrade_dt
