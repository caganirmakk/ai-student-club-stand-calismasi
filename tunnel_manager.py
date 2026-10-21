import os
import re
import sys
import shutil
import subprocess
import threading
import time
from typing import Optional, Tuple

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

TUNNEL_URL_FILE = os.path.join(os.path.dirname(__file__), "static", ".tunnel_url")

def find_cloudflared() -> Optional[str]:
    """Sistemde kurulu cloudflared yürütülebilir dosyasını tespit eder."""
    # 1. PATH kontrolü
    cmd_path = shutil.which("cloudflared")
    if cmd_path:
        return cmd_path

    # 2. Standart Windows ve macOS Kurulum Yolları
    candidates = [
        # Windows
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"),
        # macOS (Homebrew Apple Silicon & Intel)
        "/opt/homebrew/bin/cloudflared",
        "/usr/local/bin/cloudflared",
        # Linux
        "/usr/bin/cloudflared"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def start_cloudflared_tunnel(local_port: int = 8000, timeout: int = 15) -> Tuple[Optional[subprocess.Popen], Optional[str]]:
    """
    Cloudflare Quick Tunnel başlatır ve dışa açık HTTPS URL'sini döner.
    Örn: https://random-words.trycloudflare.com
    """
    exe = find_cloudflared()
    if not exe:
        print("⚠️ [Tunnel] cloudflared bulunamadı. Yerel ağ modu kullanılacak.")
        return None, None

    cmd = [exe, "tunnel", "--url", f"http://127.0.0.1:{local_port}"]
    print("🌐 [Tunnel] Cloudflare tüneli oluşturuluyor...")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )
    except Exception as e:
        print(f"❌ [Tunnel] Başlatma hatası: {e}")
        return None, None

    found_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")

    # Cloudflared loglarını arka planda tüketirken URL'yi yakala
    start_time = time.time()
    
    def read_stderr():
        nonlocal found_url
        for line in proc.stderr:
            match = url_pattern.search(line)
            if match and not found_url:
                found_url = match.group(0)

    t = threading.Thread(target=read_stderr, daemon=True)
    t.start()

    while time.time() - start_time < timeout:
        if found_url:
            break
        if proc.poll() is not None:
            print("❌ [Tunnel] cloudflared beklenmedik şekilde kapandı.")
            break
        time.sleep(0.3)

    if found_url:
        try:
            with open(TUNNEL_URL_FILE, "w", encoding="utf-8") as f:
                f.write(found_url.strip())
        except Exception:
            pass
        return proc, found_url
    else:
        print("⚠️ [Tunnel] Tünel adresi zaman aşımına uğradı. Yerel ağa geçiliyor.")
        return proc, None

def stop_cloudflared_tunnel(proc: Optional[subprocess.Popen]):
    """Tüneli sonlandırır ve geçici url dosyasını siler."""
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    if os.path.exists(TUNNEL_URL_FILE):
        try:
            os.remove(TUNNEL_URL_FILE)
        except Exception:
            pass

def get_current_tunnel_url() -> Optional[str]:
    """Kayıtlı aktif tünel adresini okur."""
    if os.path.exists(TUNNEL_URL_FILE):
        try:
            with open(TUNNEL_URL_FILE, "r", encoding="utf-8") as f:
                url = f.read().strip()
                if url.startswith("https://"):
                    return url
        except Exception:
            pass
    return None

if __name__ == "__main__":
    p, url = start_cloudflared_tunnel(8000)
    print("URL:", url)
    if p:
        time.sleep(5)
        stop_cloudflared_tunnel(p)
