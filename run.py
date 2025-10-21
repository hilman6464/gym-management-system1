from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print("🚀 سیستم مدیریت باشگاه ورزشی در حال اجرا...")
    print(f"📍 پورت: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
