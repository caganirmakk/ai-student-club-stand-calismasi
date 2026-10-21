import os
import re
import time
import base64
import logging
from io import BytesIO
from pydantic import BaseModel
from PIL import Image
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from cleanup_daemon import start_cleanup_daemon, DEFAULT_TTL_SECONDS, CARDS_DIR, SNAPS_DIR
from network_utils import get_candidate_ips, get_primary_stand_ip

SERVER_START_TIME = time.time()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="Altınbaş AI Club - Mobil İndirme ve Stand API Servisi")

# P1: CORS Sıkılaştırma - Sadece yerel Streamlit arayüzüne izin ver
allowed_origins = [
    "http://localhost:8501",
    "http://127.0.0.1:8501"
]
for ip in get_candidate_ips():
    allowed_origins.append(f"http://{ip}:8501")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https:\/\/.*\.trycloudflare\.com$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Arka plan temizleme servisini başlat
start_cleanup_daemon(ttl_seconds=DEFAULT_TTL_SECONDS, interval=20)

os.makedirs(CARDS_DIR, exist_ok=True)
os.makedirs(SNAPS_DIR, exist_ok=True)

class SnapPayload(BaseModel):
    session_token: str
    image_base64: str

TOKEN_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")

# P0: Oturum bazlı ham fotoğraf kaydı & doğrulama
@app.post("/api/save-snap")
async def save_snap(payload: SnapPayload):
    token = payload.session_token.strip()
    if not token or not TOKEN_PATTERN.match(token) or len(token) > 64:
        raise HTTPException(status_code=400, detail="Geçersiz oturum anahtarı (session token).")

    # Boyut kontrolü (max 7MB base64 ~ 5MB ikili veri)
    if len(payload.image_base64) > 7 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Görsel verisi çok büyük (Max 5MB).")

    try:
        raw_b64 = payload.image_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(raw_b64)

        # Pillow ile görsel bütünlük ve format doğrulaması
        with Image.open(BytesIO(img_bytes)) as pil_img:
            if pil_img.format not in ("PNG", "JPEG", "WEBP"):
                raise HTTPException(status_code=400, detail="Desteklenmeyen görsel formatı.")
            w, h = pil_img.size
            if w < 100 or h < 100 or w > 4000 or h > 4000:
                raise HTTPException(status_code=400, detail="Geçersiz görsel boyutları.")

        target_path = os.path.join(SNAPS_DIR, f"{token}.png")
        with open(target_path, "wb") as f:
            f.write(img_bytes)

        return {"status": "ok", "session_token": token, "message": "Fotoğraf güvenle oturuma kaydedildi"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fotoğraf işleme hatası: {str(e)}")

# P2: Stant ve Sunucu Sağlık Kontrolü Endpoint'i
@app.get("/health")
async def health_check():
    cards_count = len([f for f in os.listdir(CARDS_DIR) if f.endswith(".png")]) if os.path.exists(CARDS_DIR) else 0
    snaps_count = len([f for f in os.listdir(SNAPS_DIR) if f.endswith(".png")]) if os.path.exists(SNAPS_DIR) else 0
    
    # Yazma izni kontrolü
    storage_ok = True
    try:
        test_file = os.path.join(CARDS_DIR, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
    except Exception:
        storage_ok = False

    return {
        "status": "healthy" if storage_ok else "degraded",
        "service": "altinbas_ai_stand",
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 1),
        "active_cards_count": cards_count,
        "active_snaps_count": snaps_count,
        "ttl_seconds": DEFAULT_TTL_SECONDS,
        "storage_writable": storage_ok,
        "stand_ips": get_candidate_ips(),
        "primary_ip": get_primary_stand_ip()
    }

# P0: Güvenli kart görseli sunma (Doğrudan statik mount kaldırıldı)
@app.get("/kart-gorsel/{card_id}")
async def serve_card_image(card_id: str):
    safe_id = os.path.basename(card_id).replace(".png", "")
    if not TOKEN_PATTERN.match(safe_id):
        raise HTTPException(status_code=400, detail="Geçersiz kart kimliği.")

    card_path = os.path.join(CARDS_DIR, f"{safe_id}.png")
    if not os.path.exists(card_path):
        raise HTTPException(status_code=404, detail="Kart bulunamadı veya süresi doldu.")

    mtime = os.path.getmtime(card_path)
    elapsed = time.time() - mtime
    if elapsed > DEFAULT_TTL_SECONDS:
        try:
            os.remove(card_path)
        except Exception:
            pass
        raise HTTPException(status_code=410, detail="Kartın 5 dakikalık süresi doldu ve kalıcı olarak silindi.")

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0, private",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    return FileResponse(card_path, media_type="image/png", headers=headers)

# Mobil Kart Önizleme Sayfası (Kullanıcı QR tarattığında açılan sayfa)
@app.get("/kart/{card_id}", response_class=HTMLResponse)
async def view_card(card_id: str):
    safe_id = os.path.basename(card_id).replace(".png", "")
    if not TOKEN_PATTERN.match(safe_id):
        raise HTTPException(status_code=400, detail="Geçersiz kart kimliği.")

    card_path = os.path.join(CARDS_DIR, f"{safe_id}.png")

    if not os.path.exists(card_path):
        return HTMLResponse(
            status_code=404,
            content="""
            <!DOCTYPE html>
            <html lang="tr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Kart Bulunamadı - Altınbaş AI Club</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-4">
                <div class="bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-md w-full text-center shadow-2xl">
                    <div class="text-5xl mb-4">⌛</div>
                    <h1 class="text-2xl font-bold mb-2">Süre Doldu veya Kart Bulunamadı</h1>
                    <p class="text-slate-400 text-sm leading-relaxed mb-6">
                        KVKK ve veri gizliliği politikamız gereği tüm kartlar üretildikten <strong>5 dakika sonra</strong> sunucumuzdan kalıcı olarak silinmektedir.
                    </p>
                    <div class="text-xs text-slate-500">
                        Altınbaş Üniversitesi Yapay Zeka Kulübü
                    </div>
                </div>
            </body>
            </html>
            """,
            headers={"Cache-Control": "no-store"}
        )

    mtime = os.path.getmtime(card_path)
    elapsed = time.time() - mtime
    if elapsed > DEFAULT_TTL_SECONDS:
        try:
            os.remove(card_path)
        except Exception:
            pass
        return HTMLResponse(
            status_code=410,
            content="""
            <!DOCTYPE html>
            <html lang="tr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Süre Doldu - Altınbaş AI Club</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-4">
                <div class="bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-md w-full text-center shadow-2xl">
                    <div class="text-5xl mb-4">🔒</div>
                    <h1 class="text-2xl font-bold mb-2">5 Dakikalık İndirme Süresi Doldu</h1>
                    <p class="text-slate-400 text-sm leading-relaxed mb-6">
                        Gizliliğinizi korumak amacıyla fotoğrafınız ve kartınız kalıcı olarak silinmiştir.
                    </p>
                    <div class="text-xs text-slate-500">
                        Altınbaş Üniversitesi Yapay Zeka Kulübü
                    </div>
                </div>
            </body>
            </html>
            """,
            headers={"Cache-Control": "no-store"}
        )

    remaining_seconds = max(0, int(DEFAULT_TTL_SECONDS - elapsed))

    html_content = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Karakter Kartın - Altınbaş AI Club</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @keyframes pulse-glow {{
                0%, 100% {{ box-shadow: 0 0 25px rgba(236, 72, 153, 0.3); }}
                50% {{ box-shadow: 0 0 40px rgba(168, 85, 247, 0.5); }}
            }}
            .glow-card {{
                animation: pulse-glow 3s infinite;
            }}
        </style>
    </head>
    <body class="bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-white min-h-screen flex flex-col items-center justify-between p-4 py-8">
        
        <header class="text-center mb-4">
            <span class="inline-block px-3 py-1 bg-indigo-500/10 border border-indigo-500/30 rounded-full text-indigo-400 text-xs font-semibold tracking-wider uppercase mb-2">
                Altınbaş AI Club • Orientation '26
            </span>
            <h1 class="text-2xl font-black tracking-tight bg-gradient-to-r from-pink-400 via-purple-300 to-indigo-400 bg-clip-text text-transparent">
                Karakter Kartın Hazır! ✨
            </h1>
        </header>

        <main class="w-full max-w-sm flex flex-col items-center">
            <div class="relative w-full rounded-2xl overflow-hidden border border-white/10 glow-card shadow-2xl bg-black/40">
                <img src="/kart-gorsel/{safe_id}" alt="AI Karakter Kartı" class="w-full h-auto object-cover block">
            </div>

            <a href="/indir/{safe_id}" download="Altinbas_AI_Kart.png" 
               class="mt-6 w-full py-4 px-6 bg-gradient-to-r from-pink-500 via-purple-600 to-indigo-600 hover:opacity-90 active:scale-95 transition-all text-white font-bold text-center rounded-xl shadow-lg shadow-purple-500/25 flex items-center justify-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>Kartı Telefonuna İndir (Story Boyutu)</span>
            </a>

            <div class="mt-4 p-3 bg-white/5 border border-white/10 rounded-xl w-full text-center">
                <div class="text-xs text-slate-400 flex items-center justify-center gap-1.5 mb-1">
                    <span>🔒 Veri Gizliliği Güvencesi</span>
                </div>
                <div class="text-xs text-amber-300 font-medium">
                    Kartınız <span id="countdown" class="font-bold font-mono text-sm underline">--:--</span> sonra kalıcı olarak silinecektir.
                </div>
            </div>
        </main>

        <footer class="mt-8 text-center text-xs text-slate-500">
            Instagram hikayende paylaşırken bizi etiketlemeyi unutma: <br>
            <span class="text-indigo-400 font-semibold">@altinbas_ai</span>
        </footer>

        <script>
            let timeLeft = {remaining_seconds};
            const countdownEl = document.getElementById('countdown');

            function updateTimer() {{
                if (timeLeft <= 0) {{
                    countdownEl.textContent = "00:00 (Silindi)";
                    setTimeout(() => location.reload(), 2000);
                    return;
                }}
                const m = Math.floor(timeLeft / 60);
                const s = timeLeft % 60;
                countdownEl.textContent = `${{m < 10 ? '0' : ''}}${{m}}:${{s < 10 ? '0' : ''}}${{s}}`;
                timeLeft--;
            }}

            updateTimer();
            setInterval(updateTimer, 1000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, headers={"Cache-Control": "no-store"})

# Kart İndirme Endpoint'i
@app.get("/indir/{card_id}")
async def download_card_file(card_id: str):
    safe_id = os.path.basename(card_id).replace(".png", "")
    if not TOKEN_PATTERN.match(safe_id):
        raise HTTPException(status_code=400, detail="Geçersiz kart kimliği.")

    card_path = os.path.join(CARDS_DIR, f"{safe_id}.png")

    if not os.path.exists(card_path):
        raise HTTPException(status_code=404, detail="Kart bulunamadı veya süresi doldu.")

    mtime = os.path.getmtime(card_path)
    if time.time() - mtime > DEFAULT_TTL_SECONDS:
        try:
            os.remove(card_path)
        except Exception:
            pass
        raise HTTPException(status_code=410, detail="Kartın süresi doldu ve kalıcı olarak silindi.")

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache"
    }

    return FileResponse(
        card_path,
        media_type="image/png",
        filename=f"Altinbas_AI_Karakter_{safe_id[:8]}.png",
        headers=headers
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("download_server:app", host="0.0.0.0", port=8000, reload=False)
