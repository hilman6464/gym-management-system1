from datetime import datetime, timedelta

class InsuranceChecker:
    def check_insurance(self, insurance_date):
        if not insurance_date:
            return None
        
        try:
            expiry_date = self._calculate_expiry_date(insurance_date)
            days_left = self._days_until(expiry_date)
            
            if days_left <= 0:
                return {
                    'type': 'insurance_expired',
                    'message': 'بیمه منقضی شده',
                    'days_left': days_left,
                    'priority': 1,
                    'css_class': 'insurance-expired'
                }
            elif days_left <= 10:
                return {
                    'type': 'insurance_urgent',
                    'message': f'{days_left} روز تا انقضای بیمه',
                    'days_left': days_left,
                    'priority': 2,
                    'css_class': 'insurance-urgent'
                }
        except Exception as e:
            print(f"خطا در بررسی بیمه: {e}")
        
        return None
    
    def _calculate_expiry_date(self, insurance_date):
        insurance_dt = datetime.strptime(insurance_date, '%Y-%m-%d')
        return insurance_dt + timedelta(days=365)
    
    def _days_until(self, target_date):
        today = datetime.now()
        return (target_date - today).days
