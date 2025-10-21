from persiantools.jdatetime import JalaliDate
from datetime import datetime

def to_jalali(date_str):
    if not date_str:
        return ''
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return JalaliDate(dt).strftime('%Y/%m/%d')
    except Exception:
        return ''
