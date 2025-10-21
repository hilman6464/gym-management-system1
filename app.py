from flask import Flask
from flask_ngrok import run_with_ngrok
import socket
from datetime import datetime

app = Flask(__name__)
run_with_ngrok(app)  # این خط مهم است!

@app.route('/')
def home():
    return """
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>🌍 برنامه شما از سراسر جهان قابل دسترسی است!</h1>
            <p>این برنامه اکنون از هر شبکه اینترنتی در دسترس است</p>
            <p>زمان سرور: {}</p>
            <p>✅ برنامه با موفقیت deploy شده است</p>
        </body>
    </html>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/test')
def test():
    return "✅ تست موفق! برنامه از اینترنت کار می‌کند"

if __name__ == '__main__':
    print("🌐 در حال راه‌اندازی سرور برای دسترسی جهانی...")
    app.run()
