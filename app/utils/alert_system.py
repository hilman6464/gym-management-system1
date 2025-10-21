from datetime import datetime, timedelta
from persiantools.jdatetime import JalaliDate
from .belt_calculator import BeltCalculator
from .insurance_checker import InsuranceChecker
from .date_calculator import DateCalculator

class AlertSystem:
    def __init__(self, db_connection=None):
        self.belt_calc = BeltCalculator()
        self.insurance_checker = InsuranceChecker()
        self.date_calc = DateCalculator()
        self.db_connection = db_connection
    
    def get_member_alerts(self, member_data):
        """دریافت تمام هشدارهای یک عضو"""
        alerts = []
        
        # هشدار بیمه
        insurance_alert = self.insurance_checker.check_insurance(member_data['insurance_date'])
        if insurance_alert:
            alerts.append(insurance_alert)
        
        # هشدار تولد
        birthday_alert = self.date_calc.get_birthday_alert(member_data['birth_date'])
        if birthday_alert:
            alerts.append(birthday_alert)
        
        # هشدار کمربند
        belt_alert = self.belt_calc.get_belt_upgrade_alert(
            member_data['belt'], 
            member_data['belt_date']
        )
        if belt_alert:
            alerts.append(belt_alert)
        
        # هشدار پرداخت
        payment_alert = self.get_payment_alert(member_data['id'])
        if payment_alert:
            alerts.append(payment_alert)
        
        # مرتب کردن بر اساس اولویت
        alerts.sort(key=lambda x: x['priority'])
        return alerts
    
    def get_payment_alert(self, member_id):
        """دریافت هشدار پرداخت از دیتابیس"""
        if not self.db_connection:
            return None
            
        try:
            c = self.db_connection.cursor()
            
            # پیدا کردن آخرین پرداخت
            c.execute('''
                SELECT payment_date FROM payments 
                WHERE member_id = ? 
                ORDER BY year DESC, month DESC 
                LIMIT 1
            ''', (member_id,))
            
            last_payment = c.fetchone()
            last_payment_date = last_payment['payment_date'] if last_payment else None
            
            return self.date_calc.get_payment_alert(member_id, last_payment_date)
            
        except Exception as e:
            print(f"خطا در دریافت هشدار پرداخت: {e}")
            return None
