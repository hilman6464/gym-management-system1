from .db import get_db_connection
from persiantools.jdatetime import JalaliDate

def get_payment_status(member_id, month, year):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM payments WHERE member_id=? AND month=? AND year=?", (member_id, month, year))
    payment = c.fetchone()
    conn.close()

    today_jalali = JalaliDate.today()

    if payment:
        return 'paid'
    elif today_jalali.day > 5:
        return 'late'
    else:
        return 'pending'
