from app import create_app
from pyngrok import ngrok, conf
import threading
import time
import atexit
import sys

class GlobalAccess:
    def __init__(self):
        self.public_url = None
        
    def setup_tunnel(self):
        """تنظیم تونل جهانی"""
        try:
            # تنظیم region برای بهتر بودن ping
            conf.get_default().region = "eu"  # یا "us", "ap"
            
            # ایجاد تونل
            self.public_url = ngrok.connect(8080, bind_tls=True)
            
            self.show_success_message()
            self.save_url_to_file()
            
        except Exception as e:
            self.show_fallback_message(e)
    
    def show_success_message(self):
        """نمایش پیام موفقیت"""
        print("\n" + "🎯" * 60)
        print("🌍 **سیستم مدیریت باشگاه ورزشی جهانی شد!**")
        print(f"🔗 لینک دسترسی: {self.public_url}")
        print("📊 امکانات فعال:")
        print("   ✅ مدیریت اعضا")
        print("   ✅ مدیریت باشگاه‌ها")
        print("   ✅ سیستم حضور و غیاب")
        print("   ✅ مدیریت پرداخت‌ها")
        print("   ✅ گزارش‌گیری پیشرفته")
        print("   ✅ سیستم بک‌آپ خودکار")
        print("📱 از هر دستگاه موبایل یا کامپیوتر قابل دسترسی است")
        print("🎯" * 60 + "\n")
    
    def show_fallback_message(self, error):
        """نمایش پیام Fallback"""
        print(f"❌ خطا در تونل جهانی: {error}")
        print("\n🔧 **دسترسی‌های جایگزین:**")
        print(f"📍 محلی: http://localhost:8080")
        print(f"🌐 شبکه: http://192.168.1.100:8080")
        print("💡 برای دسترسی جهانی از localtunnel استفاده کنید:")
        print("   npx localtunnel --port 8080")
    
    def save_url_to_file(self):
        """ذخیره لینک در فایل"""
        try:
            with open("global_access.txt", "w", encoding="utf-8") as f:
                f.write("=" * 50 + "\n")
                f.write("لینک دسترسی جهانی - سیستم مدیریت باشگاه\n")
                f.write("=" * 50 + "\n")
                f.write(f"🌍 آدرس: {self.public_url}\n")
                f.write(f"⏰ تاریخ: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("📱 از مرورگر موبایل یا کامپیوتر باز کنید\n")
                f.write("=" * 50 + "\n")
            print("✅ اطلاعات دسترسی در 'global_access.txt' ذخیره شد")
        except Exception as e:
            print(f"⚠️ خطا در ذخیره فایل: {e}")

def cleanup():
    """تمیزکاری هنگام خروج"""
    try:
        ngrok.kill()
        print("🛑 تونل جهانی بسته شد")
    except:
        pass

# ثبت تابع cleanup
atexit.register(cleanup)

# ایجاد برنامه
app = create_app()

def start_global_access():
    """شروع دسترسی جهانی"""
    time.sleep(7)  # زمان برای لود کامل سیستم بک‌آپ و دیتابیس
    global_access = GlobalAccess()
    global_access.setup_tunnel()

if __name__ == '__main__':
    print("🚀 راه‌اندازی سیستم مدیریت باشگاه ورزشی...")
    print("⏳ در حال بارگذاری ماژول‌ها و سیستم بک‌آپ...")
    
    # شروع دسترسی جهانی
    access_thread = threading.Thread(target=start_global_access, daemon=True)
    access_thread.start()
    
    # اجرای برنامه اصلی
    try:
        app.run(host='0.0.0.0', port=8080, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 برنامه متوقف شد")
        cleanup()
        sys.exit(0)
