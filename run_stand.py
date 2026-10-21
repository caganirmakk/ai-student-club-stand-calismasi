import os
import sys
import subprocess
import time
import signal
from tunnel_manager import start_cloudflared_tunnel, stop_cloudflared_tunnel, find_cloudflared

# Windows konsolunda UTF-8 desteği
if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr:
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def main():
    use_tunnel = "--no-tunnel" not in sys.argv
    current_dir = os.path.dirname(os.path.abspath(__file__))

    print("==================================================")
    print("🚀 ALTINBAŞ AI CLUB • KARAKTER KARTI STAND SERVİSİ")
    print("==================================================")

    # 1. FastAPI Mobil İndirme Sunucusu Başlatılıyor (Port 8000)
    print("📡 [1/3] Mobil indirme sunucusu (FastAPI :8000) başlatılıyor...")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "download_server:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=current_dir
    )

    time.sleep(1.5)

    # 2. Cloudflare Canlı Tünel Başlatılıyor
    tunnel_proc = None
    tunnel_url = None
    if use_tunnel:
        if find_cloudflared():
            print("🌐 [2/3] Cloudflare canlı HTTPS tüneli açılıyor...")
            tunnel_proc, tunnel_url = start_cloudflared_tunnel(local_port=8000, timeout=12)
        else:
            print("ℹ️ [2/3] cloudflared bulunamadı, yerel ağ modunda devam ediliyor.")
    else:
        print("ℹ️ [2/3] Tünel devre dışı bırakıldı (--no-tunnel), yerel ağ modunda çalışılıyor.")

    # 3. Streamlit Stant Arayüzü Başlatılıyor (Port 8501)
    print("💻 [3/3] Streamlit stant arayüzü (:8501) başlatılıyor...")
    st_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"],
        cwd=current_dir
    )

    print("\n" + "="*50)
    print("✅ TÜM SERVİSLER BAŞARIYLA ÇALIŞIYOR!")
    print("="*50)
    print("💻 Stant Kiosk Ekranı : http://localhost:8501")
    print("📡 Yerel API Servisi   : http://localhost:8000")
    if tunnel_url:
        print(f"🌍 CANLI MOBİL ERİŞİM  : {tunnel_url}")
        print("   (Ziyaretçiler kendi 4G/5G'sinde bile olsa QR ile bu linki açabilir!)")
    else:
        print("📶 Yerel Ağ Modu      : Telefonların stant Wi-Fi / Hotspot ağına bağlı olması gerekir.")
    print("="*50)
    print("Durdurmak için terminalde Ctrl+C tuşlayın.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Servisler güvenle kapatılıyor...")
        if tunnel_proc:
            stop_cloudflared_tunnel(tunnel_proc)
        api_proc.terminate()
        st_proc.terminate()
        print("👋 Görüşmek üzere!")

if __name__ == "__main__":
    main()
