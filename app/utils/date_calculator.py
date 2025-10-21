from datetime import datetime, timedelta
from persiantools.jdatetime import JalaliDate

class DateCalculator:
    def get_birthday_alert(self, birth_date):
        """هشدار 5 روز مانده به تولد"""
        if not birth_date:
            return None
        
        days_left = self._days_to_birthday(birth_date)
        
        if 0 < days_left <= 5:
            return {
                'type': 'birthday',
                'message': f'🎂 {days_left} روز تا تولد',
                'days_left': days_left,
                'priority': 4,
                'css_class': 'birthday-alert'
            }
        
        return None
    
    def get_payment_alert(self, member_id, last_payment_date):
        """هشدار 10 روز مانده به پرداخت"""
        if not last_payment_date:
            return {
                'type': 'payment_missing',
                'message': '💰 پرداخت ثبت نشده',
                'days_left': -1,
                'priority': 1,
                'css_class': 'payment-missing'
            }
        
        days_left = self._days_to_payment_deadline(last_payment_date)
        
        if 0 < days_left <= 10:
            return {
                'type': 'payment_due',
                'message': f'💰 {days_left} روز تا پرداخت',
                'days_left': days_left,
                'priority': 2,
                'css_class': 'payment-alert'
            }
        
        return None
    
    def _days_to_birthday(self, birth_date):
        """محاسبه روزهای مانده به تولد بعدی"""
        try:
            # تبدیل تاریخ تولد به میلادی
            birth_dt = datetime.strptime(birth_date, '%Y-%m-%d')
            today = datetime.now()
            
            # تولد امسال
            birthday_this_year = datetime(today.year, birth_dt.month, birth_dt.day)
            
            # اگر تولد امسال گذشته، تولد سال بعد
            if birthday_this_year < today:
                birthday_this_year = datetime(today.year + 1, birth_dt.month, birth_dt.day)
            
            # محاسبه روزهای مانده
            days_left = (birthday_this_year - today).days
            return days_left
            
        except Exception as e:
            print(f"خطا در محاسبه تولد: {e}")
            return None
    
    def _days_to_payment_deadline(self, last_payment_date):
        """محاسبه روزهای مانده به مهلت پرداخت بعدی"""
        try:
            last_payment_dt = datetime.strptime(last_payment_date, '%Y-%m-%d')
            today = datetime.now()
            
            # مهلت پرداخت بعدی (1 ماه بعد از آخرین پرداخت)
            next_deadline = last_payment_dt + timedelta(days=30)
            
            # محاسبه روزهای مانده
            days_left = (next_deadline - today).days
            return days_left
            
        except Exception as e:
            print(f"خطا در محاسبه مهلت پرداخت: {e}")
            return None
    
    def _days_until(self, target_date):
        """محاسبه روزهای مانده تا یک تاریخ"""
        today = datetime.now()
        return (target_date - today).days
    
    def jalali_to_gregorian(self, jalali_date_str):
        """تبدیل تاریخ شمسی به میلادی"""
        try:
            parts = list(map(int, jalali_date_str.split('/')))
            if len(parts) != 3:
                return None
            jalali_date = JalaliDate(parts[0], parts[1], parts[2])
            return jalali_date.to_gregorian()
        except:
            return None
    
    def gregorian_to_jalali(self, gregorian_date):
        """تبدیل تاریخ میلادی به شمسی"""
        try:
            if isinstance(gregorian_date, str):
                gregorian_date = datetime.strptime(gregorian_date, '%Y-%m-%d')
            jalali_date = JalaliDate(gregorian_date)
            return jalali_date.strftime('%Y/%m/%d')
        except:
            return None
