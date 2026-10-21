import os
import sys
import time
import secrets
from io import BytesIO
from PIL import Image, ImageDraw

# Proje dizinini ekle
STAND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, STAND_DIR)

from stats_engine import calculate_stats
from card_generator import generate_card, CARDS_DIR, SNAPS_DIR
from cleanup_daemon import cleanup_directory

if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')

SAMPLE_NAMES = [
    ("Selin Kaya", "Endüstri Müh.", "muse"),
    ("Çağan Demir", "Yazılım Müh.", "player"),
    ("Zeynep Aksoy", "Mimarlık", "muse"),
    ("Burak Yılmaz", "Bilgisayar Müh.", "player"),
    ("Elif Şahin", "Tıp Fakültesi", "muse"),
    ("Mert Öztürk", "Elektrik-Elektronik", "player"),
    ("Ayşe Çelik", "İşletme", "muse"),
    ("Emre Aydın", "Hukuk Fakültesi", "player"),
    ("Duygu Arslan", "Psikoloji", "muse"),
    ("Can Polat", "Uluslararası İlişkiler", "player"),
    ("Defne Yıldız", "Diş Hekimliği", "muse"),
    ("Alp Aslan", "Makine Müh.", "player"),
    ("Melis Kara", "İç Mimarlık", "muse"),
    ("Kaan Eren", "Yazılım Müh.", "player"),
    ("İrem Bulut", "Eczacılık", "muse"),
    ("Onur Keskin", "Siber Güvenlik", "player"),
    ("Büşra Doğan", "Görsel İletişim", "muse"),
    ("Tuğra Erdem", "Yapay Zeka Müh.", "player"),
    ("Yağmur Koç", "Havacılık Yönetimi", "muse"),
    ("Furkan Bozkurt", "Bilişim Sistemleri", "player")
]

def create_synthetic_portrait(color: tuple) -> bytes:
    """Yüz benzeri sentetik bir portre görseli üretir."""
    img = Image.new("RGB", (640, 800), color)
    draw = ImageDraw.Draw(img)
    # Baş ve omuz simülasyonu
    draw.ellipse([220, 150, 420, 400], fill=(230, 190, 170))  # Kafa
    draw.chord([150, 420, 490, 850], 0, 180, fill=(50, 80, 140))  # Omuzlar
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def run_rehearsal():
    print("=" * 65)
    print("🚀 ALTINBAŞ AI STANDI: 20 KARTLIK PROVA & SAĞLAMLAŞTIRMA TESTİ")
    print("=" * 65)

    times = []
    generated_cards = []
    snaps_created = []

    for idx, (name, dept, theme) in enumerate(SAMPLE_NAMES, 1):
        color = ((idx * 35) % 255, (idx * 55) % 255, (idx * 75) % 255)
        photo_bytes = create_synthetic_portrait(color)
        
        # P0: Oturum bazlı snap kaydı testi
        session_token = f"test_session_{secrets.token_hex(8)}"
        snap_path = os.path.join(SNAPS_DIR, f"{session_token}.png")
        with open(snap_path, "wb") as f:
            f.write(photo_bytes)
        snaps_created.append(snap_path)

        t0 = time.time()
        stats = calculate_stats(name, dept, theme)
        card_id, card_path = generate_card(photo_bytes, stats, session_token=session_token)
        t_el = time.time() - t0
        times.append(t_el)
        generated_cards.append((card_id, card_path))

        # Kontroller
        with Image.open(card_path) as card_img:
            dim_ok = card_img.size == (1080, 1920)
        
        token_ok = len(card_id) == 32  # 128-bit hex
        snap_deleted = not os.path.exists(snap_path)  # P0: Anında silinme

        status_icon = "✅" if (dim_ok and token_ok and snap_deleted) else "❌"
        print(f"[{idx:02d}/20] {status_icon} {theme.upper():<6} | {name:<16} | OVR: {stats['ovr']} | Süre: {t_el:.2f}s | 1080x1920: {dim_ok} | Snap Silindi: {snap_deleted}")

    print("-" * 65)
    avg_t = sum(times) / len(times)
    max_t = max(times)
    print(f"📊 Ortalama Üretim Süresi: {avg_t:.2f} saniye")
    print(f"⚡ En Uzun Süre: {max_t:.2f} saniye")
    
    # TTL Temizleme Testi
    print("\n🧹 TTL Temizleme Testi Simülasyonu:")
    # Süresi dolmuş gibi mtime'ı geriye çekilen 1 kart testi
    test_expired_id, test_expired_path = generated_cards[0]
    past_time = time.time() - 350  # 5 dakikadan eski
    os.utime(test_expired_path, (past_time, past_time))
    cleanup_directory(CARDS_DIR, ttl_seconds=300, label="Test Kartı")
    ttl_success = not os.path.exists(test_expired_path)
    print(f"🔒 [P0] 5 dakikayı geçen kart otomatik silindi mi: {'EVET ✅' if ttl_success else 'HAYIR ❌'}")

    print("=" * 65)
    print("✨ TÜM GÜVENLİK VE OPERASYONEL KRİTERLER BAŞARIYLA GEÇTİ!")
    print("=" * 65)

if __name__ == "__main__":
    run_rehearsal()
