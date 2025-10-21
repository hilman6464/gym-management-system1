import requests
import threading
import time

def test_public_access(public_url):
    """تست دسترسی عمومی"""
    try:
        response = requests.get(public_url, timeout=10)
        if response.status_code == 200:
            print(f"✅ دسترسی عمومی موفق: {public_url}")
            return True
        else:
            print(f"⚠️ خطا در دسترسی: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ خطا در اتصال: {e}")
        return False

def start_localhost_run_tunnel():
    """شروع تونل با localhost.run"""
    import subprocess
    try:
        print("🌐 در حال اتصال به localhost.run...")
        process = subprocess.Popen([
            'powershell', '-Command', 
            'ssh -o StrictHostKeyChecking=no -R 80:localhost:8080 localhost.run'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # خواندن خروجی
        for line in process.stdout:
            print(line.strip())
            if 'localhost.run' in line and 'http' in line:
                public_url = line.strip()
                print(f"🎉 لینک عمومی: {public_url}")
                
                # تست دسترسی
                test_public_access(public_url)
                
    except Exception as e:
        print(f"❌ خطا: {e}")
        print("📋 لطفاً دستی از PowerShell استفاده کنید")

if __name__ == "__main__":
    print("🔗 تست اتصال جهانی...")
    
    # بررسی که برنامه در حال اجراست
    try:
        response = requests.get("http://localhost:8080", timeout=5)
        print("✅ برنامه محلی در حال اجراست")
        
        # شروع تونل
        tunnel_thread = threading.Thread(target=start_localhost_run_tunnel)
        tunnel_thread.daemon = True
        tunnel_thread.start()
        
        # نگه داشتن برنامه
        while True:
            time.sleep(1)
            
    except:
        print("❌ برنامه اجرا نیست. اول 'python run.py' را اجرا کنید")
