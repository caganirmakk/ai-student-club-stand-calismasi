import os
import sys
import time
import threading
import logging

if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEFAULT_TTL_SECONDS = 300  # 5 dakika
BASE_DIR = os.path.dirname(__file__)
CARDS_DIR = os.path.join(BASE_DIR, "static", "cards")
SNAPS_DIR = os.path.join(BASE_DIR, "static", "snaps")

os.makedirs(CARDS_DIR, exist_ok=True)
os.makedirs(SNAPS_DIR, exist_ok=True)

_stop_event = threading.Event()

def cleanup_directory(target_dir: str, ttl_seconds: int = DEFAULT_TTL_SECONDS, label: str = "Dosya"):
    if not os.path.exists(target_dir):
        return

    now = time.time()
    for filename in os.listdir(target_dir):
        if not filename.endswith(".png"):
            continue

        filepath = os.path.join(target_dir, filename)
        try:
            file_mtime = os.path.getmtime(filepath)
            age = now - file_mtime
            if age > ttl_seconds:
                os.remove(filepath)
                logging.info(f"🔒 [KVKK Temizleme] 5 dakikayı geçen {label} kalıcı silindi: {filename} (Yaş: {int(age)}s)")
        except Exception as e:
            logging.error(f"Dosya silinirken hata: {filepath} - {e}")

def run_cleanup_loop(ttl_seconds: int = DEFAULT_TTL_SECONDS, interval: int = 20):
    logging.info("🧹 Kart ve ham fotoğraf temizleme servisi başlatıldı (TTL: 5 dk).")
    while not _stop_event.is_set():
        cleanup_directory(CARDS_DIR, ttl_seconds, label="Kart")
        cleanup_directory(SNAPS_DIR, ttl_seconds, label="Ham Fotoğraf")
        _stop_event.wait(interval)

def start_cleanup_daemon(ttl_seconds: int = DEFAULT_TTL_SECONDS, interval: int = 20):
    thread = threading.Thread(
        target=run_cleanup_loop,
        args=(ttl_seconds, interval),
        daemon=True,
        name="CleanupDaemon"
    )
    thread.start()
    return thread

def stop_cleanup_daemon():
    _stop_event.set()

if __name__ == "__main__":
    start_cleanup_daemon()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_cleanup_daemon()
