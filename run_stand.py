import os
import sys
import subprocess
import time
import signal

# Windows konsolunda UTF-8 desteği
if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    print("==================================================")
    print("🚀 ALTINBAŞ AI CLUB • KARAKTER KARTI STAND SERVİSİ")
    print("==================================================")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. FastAPI Mobil İndirme Sunucusu Başlatılıyor (Port 8000)
    print("📡 [1/2] Mobil indirme sunucusu (FastAPI :8000) başlatılıyor...")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "download_server:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=current_dir
    )
    
    time.sleep(1.5)
    
    # 2. Streamlit Stant Arayüzü Başlatılıyor (Port 8501)
    print("💻 [2/2] Streamlit stant arayüzü (:8501) başlatılıyor...")
    st_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"],
        cwd=current_dir
    )
    
    print("\n✅ TÜM SERVİSLER ÇALIŞIYOR!")
    print("👉 Stant Laptop Ekranı: http://localhost:8501")
    print("👉 Mobil İndirme Sunucusu: http://localhost:8000")
    print("Durdurmak için Ctrl+C tuşlayın.\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Servisler kapatılıyor...")
        api_proc.terminate()
        st_proc.terminate()
        print("Görüşmek üzere!")

if __name__ == "__main__":
    main()
