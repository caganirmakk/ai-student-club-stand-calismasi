import os
import time
import secrets
import qrcode
import urllib.request
import json
from io import BytesIO
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

from stats_engine import calculate_stats
from card_generator import generate_card, CARDS_DIR, SNAPS_DIR
from network_utils import get_candidate_ips, get_primary_stand_ip, get_primary_base_url
from tunnel_manager import get_current_tunnel_url

# Sayfa yapılandırması
st.set_page_config(
    page_title="Altınbaş AI Club • Karakter Kartı Standı",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# P0: Oturum Bazlı Token Yönetimi (Ziyaretçilerin birbirinin fotoğrafını ezmesini engeller)
if "session_token" not in st.session_state:
    st.session_state["session_token"] = secrets.token_hex(16)
session_token = st.session_state["session_token"]

candidate_ips = get_candidate_ips()
primary_ip = get_primary_stand_ip()

# Modern Modüler Arayüz CSS'i
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .header-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        background: linear-gradient(90deg, rgba(236, 72, 153, 0.12), rgba(99, 102, 241, 0.12));
        border: 1px solid rgba(168, 85, 247, 0.35);
        color: #c084fc;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    
    .hero-title {
        background: linear-gradient(135deg, #f472b6 0%, #c084fc 45%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.3rem;
        line-height: 1.15;
        margin-bottom: 0.3rem;
    }
    
    .hero-desc {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 1.4rem;
    }
    
    .modular-card {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 1.3rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(12px);
    }
    
    .modular-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.1rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.9rem;
    }
    
    .step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: #8b5cf6;
        color: white;
        font-size: 0.8rem;
        font-weight: 800;
    }
    
    .stButton>button, .stDownloadButton>button {
        background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 50%, #6366f1 100%) !important;
        color: white !important;
        font-weight: 800 !important;
        font-size: 1.1rem !important;
        letter-spacing: 0.02em !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 16px !important;
        padding: 0.95rem 2rem !important;
        box-shadow: 0 8px 28px rgba(139, 92, 246, 0.4) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        width: 100% !important;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 10px 35px rgba(236, 72, 153, 0.55) !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
    }
    .stButton>button:active, .stDownloadButton>button:active {
        transform: translateY(0) scale(0.99) !important;
    }
    
    .qr-container {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# 1. Üst Bar ve Başlık
col_title, col_settings = st.columns([3.8, 1.4])
with col_title:
    st.markdown('<div class="header-badge">✨ ALTINBAŞ UNIVERSITY AI CLUB • ORYANTASYON 2026</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Karakter Kartı Standı</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-desc">Fotoğrafınızı çekin, kartınızı hazırlayalım; Instagram Story formatında telefonunuza indirin!</div>', unsafe_allow_html=True)

with col_settings:
    with st.expander("⚙️ Ağ & Mobil Erişim", expanded=False):
        current_tunnel = get_current_tunnel_url()
        if current_tunnel:
            st.success(f"🌐 **Canlı Tünel Aktif!**\n\n`{current_tunnel}`")
            st.caption("✨ Ziyaretçiler telefonlarından Wi-Fi'a bağlanmak zorunda olmadan indirebilir.")
        else:
            st.info("📶 **Yerel Ağ Modu:** Telefonların stant Wi-Fi / Hotspot ağına bağlı olması gerekir.")

        default_base = get_primary_base_url()
        host_choice = st.text_input("QR Hedef URL:", value=default_base)
        
        selected_ip = st.selectbox("Yerel IP Alternatifleri:", options=candidate_ips, index=0)
        
        if st.button("🩺 Bağlantı & Sağlık Testi", use_container_width=True):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:8000/health", headers={'User-Agent': 'StandCheck/1.0'})
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    h_data = json.loads(resp.read().decode())
                    st.success(f"✅ Sistem Hazır! (Aktif Kartlar: {h_data['active_cards_count']})")
            except Exception as e:
                st.error(f"❌ Servis Hatası: {e}")

# 2. Ana Alan: Sol (Modüler Form & Kamera), Sağ (Canlı Kart & QR)
col_left, col_right = st.columns([1.1, 1], gap="large")

with col_left:
    # MODÜL 1: Ziyaretçi Bilgileri & Stil Seçimi
    st.markdown("""
    <div class="modular-card">
        <div class="modular-header">
            <span class="step-num">1</span>
            <span>Kimlik ve Şablon Seçimi</span>
        </div>
    """, unsafe_allow_html=True)
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        name = st.text_input("Ad Soyad:", placeholder="Örn: Selin Kaya veya Çağan Demir")
    with col_input2:
        dept = st.text_input("Bölüm (Opsiyonel):", placeholder="Örn: Yazılım Mühendisliği")
    
    theme_choice = st.radio(
        "Kart Teması Seçin:",
        options=[
            "🌸 Muse Edition (Pastel Gül Altın & Işıltı)",
            "⚽ Player Card • Football Edition (Koyu Karbon, Altın & Neon Stadyum)"
        ],
        index=0,
        horizontal=False
    )
    theme_key = "muse" if "Muse" in theme_choice else "player"
    st.markdown("</div>", unsafe_allow_html=True)

    # MODÜL 2: Fotoğrafını Belirle
    st.markdown("""
    <div class="modular-card">
        <div class="modular-header">
            <span class="step-num">2</span>
            <span>Fotoğraf Çekimi veya Yükleme</span>
        </div>
    """, unsafe_allow_html=True)
    
    source_mode = st.radio(
        "Görsel Kaynağı:",
        options=["🎥 Canlı Kamera Çekimi", "📁 Bilgisayardan Fotoğraf Yükle"],
        index=0,
        horizontal=True
    )

    photo_bytes = None

    if source_mode == "🎥 Canlı Kamera Çekimi":
        # Canlı Kamera ve Buton (Kartın Portre Boyutuna Birebir Uyumlu)
        components.html(f"""
        <div style="font-family: 'Plus Jakarta Sans', sans-serif; color: white;">
            <!-- Kartın Portre Çerçevesine Birebir Uygun Kamera Vizörü -->
            <div style="position: relative; width: 280px; height: 350px; margin: 0 auto 14px auto; background: #020617; border-radius: 26px; overflow: hidden; border: 2px solid rgba(168, 85, 247, 0.45); box-shadow: 0 10px 30px rgba(0,0,0,0.6), 0 0 25px rgba(168, 85, 247, 0.2);">
                <video id="liveVideo" autoplay playsinline style="width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1);"></video>
                
                <!-- Üst Canlı Rozeti -->
                <div style="position: absolute; top: 12px; left: 12px; background: rgba(0,0,0,0.65); backdrop-filter: blur(4px); border: 1px solid rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; color: #f43f5e; display: flex; align-items: center; gap: 6px; z-index: 2;">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background: #f43f5e; display: inline-block;"></span> CANLI
                </div>
                
                <!-- Kart Çerçevesi Hizalama Rehberi -->
                <div style="position: absolute; inset: 12px; border: 1.5px dashed rgba(255, 255, 255, 0.35); border-radius: 20px; pointer-events: none; z-index: 2; display: flex; flex-direction: column; justify-content: space-between; align-items: center; padding: 8px;">
                    <span style="font-size: 0.7rem; font-weight: 600; color: rgba(255,255,255,0.7); background: rgba(0,0,0,0.55); backdrop-filter: blur(4px); padding: 2px 10px; border-radius: 12px;">Kart Çerçevesi</span>
                    <span style="font-size: 0.7rem; font-weight: 600; color: rgba(255,255,255,0.7); background: rgba(0,0,0,0.55); backdrop-filter: blur(4px); padding: 2px 10px; border-radius: 12px;">👤 Baş ve Omuzları Hizalayın</span>
                </div>
                
                <canvas id="liveCanvas" style="display: none;"></canvas>
            </div>
            
            <!-- Kontrol Butonları -->
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 10px; max-width: 330px; margin: 0 auto 10px auto;">
                <button id="snapBtn" onclick="takeSnapshot()" disabled style="display: flex; align-items: center; justify-content: center; gap: 8px; height: 46px; background: linear-gradient(135deg, #ec4899, #8b5cf6); color: white; border: none; border-radius: 12px; font-weight: 700; font-size: 0.95rem; cursor: pointer; box-shadow: 0 4px 15px rgba(236,72,153,0.35); transition: all 0.2s; outline: none; opacity: 0.6;">
                    <span>📸</span> <span>Fotoğrafı Yakala</span>
                </button>
                <button onclick="restartCamera()" style="display: flex; align-items: center; justify-content: center; gap: 6px; height: 46px; background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.18); color: #cbd5e1; border-radius: 12px; font-weight: 600; font-size: 0.88rem; cursor: pointer; transition: all 0.2s; outline: none;">
                    <span>🔄</span> <span>Yenile</span>
                </button>
            </div>

            <!-- Bilgilendirme Çubuğu -->
            <div id="camStatus" style="font-size: 0.84rem; padding: 8px 12px; border-radius: 10px; background: #0f172a; border: 1px solid rgba(255,255,255,0.08); color: #fcd34d; text-align: center; display: flex; align-items: center; justify-content: center; min-height: 38px; max-width: 330px; margin: 0 auto;">
                ⏳ Kamera başlatılıyor...
            </div>
        </div>

        <script>
            let currentStream = null;
            const sessionToken = "{session_token}";

            function stopStream() {{
                if (currentStream) {{
                    currentStream.getTracks().forEach(t => t.stop());
                    currentStream = null;
                }}
            }}

            window.addEventListener('beforeunload', stopStream);
            window.addEventListener('pagehide', stopStream);

            async function initCamera() {{
                const status = document.getElementById('camStatus');
                const video = document.getElementById('liveVideo');
                const snapBtn = document.getElementById('snapBtn');
                snapBtn.disabled = true;
                snapBtn.style.opacity = '0.6';
                snapBtn.style.cursor = 'not-allowed';
                status.innerText = "⏳ Kameraya erişim talep ediliyor...";
                status.style.background = "#0f172a";
                status.style.color = "#fcd34d";

                stopStream();

                try {{
                    const stream = await navigator.mediaDevices.getUserMedia({{
                        video: {{ facingMode: 'user', width: {{ ideal: 640 }}, height: {{ ideal: 480 }} }},
                        audio: false
                    }});
                    currentStream = stream;
                    video.srcObject = stream;
                    snapBtn.disabled = false;
                    snapBtn.style.opacity = '1';
                    snapBtn.style.cursor = 'pointer';
                    status.innerHTML = "✨ Kamera aktif. Poz verip <strong>'Fotoğrafı Yakala'</strong> butonuna basın.";
                    status.style.background = "rgba(16, 185, 129, 0.15)";
                    status.style.border = "1px solid rgba(16, 185, 129, 0.4)";
                    status.style.color = "#6ee7b7";
                }} catch (err) {{
                    status.innerHTML = `❌ <strong>[${{err.name}}]:</strong> ${{err.message}}`;
                    status.style.background = "rgba(239, 68, 68, 0.15)";
                    status.style.border = "1px solid rgba(239, 68, 68, 0.4)";
                    status.style.color = "#fca5a5";
                }}
            }}

            function restartCamera() {{
                const snapBtn = document.getElementById('snapBtn');
                snapBtn.innerHTML = "<span>📸</span> <span>Fotoğrafı Yakala</span>";
                stopStream();
                setTimeout(initCamera, 300);
            }}

            async function takeSnapshot() {{
                const video = document.getElementById('liveVideo');
                const canvas = document.getElementById('liveCanvas');
                const status = document.getElementById('camStatus');
                const snapBtn = document.getElementById('snapBtn');
                
                snapBtn.innerHTML = "<span>⏳ Aktarılıyor...</span>";
                snapBtn.disabled = true;

                const vw = video.videoWidth || 640;
                const vh = video.videoHeight || 480;
                const targetRatio = 280 / 350;

                let cropW, cropH, cropX, cropY;
                if ((vw / vh) > targetRatio) {{
                    cropH = vh;
                    cropW = vh * targetRatio;
                    cropX = (vw - cropW) / 2;
                    cropY = 0;
                }} else {{
                    cropW = vw;
                    cropH = vw / targetRatio;
                    cropX = 0;
                    cropY = (vh - cropH) / 2;
                }}

                canvas.width = 1120;
                canvas.height = 1400;
                const ctx = canvas.getContext('2d');
                
                ctx.save();
                ctx.translate(canvas.width, 0);
                ctx.scale(-1, 1);
                ctx.drawImage(video, cropX, cropY, cropW, cropH, 0, 0, canvas.width, canvas.height);
                ctx.restore();
                
                const b64 = canvas.toDataURL('image/png');
                status.innerHTML = "⏳ Fotoğraf stanta aktarılıyor...";
                
                try {{
                    const host = window.location.hostname || 'localhost';
                    const res = await fetch(`http://${{host}}:8000/api/save-snap`, {{
                        method: 'POST',
                        mode: 'cors',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ session_token: sessionToken, image_base64: b64 }})
                    }});
                    if (res.ok) {{
                        snapBtn.innerHTML = "<span>✅ Fotoğraf Çekildi</span>";
                        snapBtn.disabled = false;
                        status.innerHTML = "🎉 <strong>Fotoğraf Hazır!</strong> Şimdi aşağıdaki butondan kartını basabilirsin.";
                        status.style.background = "rgba(139, 92, 246, 0.2)";
                        status.style.border = "1px solid rgba(139, 92, 246, 0.4)";
                        status.style.color = "#ddd6fe";
                    }}
                }} catch (e) {{
                    status.innerHTML = "❌ Kaydetme hatası: " + e;
                    snapBtn.disabled = false;
                    snapBtn.innerHTML = "<span>📸</span> <span>Fotoğrafı Yakala</span>";
                }}
            }}

            initCamera();
        </script>
        """, height=490)

        # P0: Oturum bazlı ham fotoğrafı oku
        snap_path = os.path.join(SNAPS_DIR, f"{session_token}.png")
        if os.path.exists(snap_path):
            with open(snap_path, "rb") as f:
                photo_bytes = f.read()
    else:
        file_photo = st.file_uploader("Fotoğraf Dosyasını Seçin", type=["jpg", "jpeg", "png"], key="modular_file_upload")
        if file_photo:
            photo_bytes = file_photo.getvalue()
            st.success("📁 Fotoğraf başarıyla yüklendi!")

    st.markdown("</div>", unsafe_allow_html=True)

    # MODÜL 3: Aksiyon Butonu
    st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
    generate_btn = st.button("✨ Karakter Kartımı Bas", use_container_width=True)

with col_right:
    st.markdown("""
    <div class="modular-card">
        <div class="modular-header">
            <span class="step-num">3</span>
            <span>Karakter Kartın & QR Kod</span>
        </div>
    """, unsafe_allow_html=True)
    
    if generate_btn:
        if not name:
            st.warning("⚠️ Lütfen adınızı ve soyadınızı yazın!")
        elif not photo_bytes:
            st.warning("⚠️ Lütfen kameradan 'Fotoğrafı Yakala' butonuna basın veya bir fotoğraf yükleyin!")
        else:
            # P1: Gerçekçi ve dürüst durum metinleri (sahte AI analizi yerine)
            status_box = st.status("🎨 Karakter kartınız hazırlanıyor...", expanded=True)
            time.sleep(0.3)
            status_box.update(label="✨ Fotoğrafınız işleniyor ve arka plan ayrıştırılıyor...")
            time.sleep(0.3)
            status_box.update(label="⚡ İstatistikler ve unvanınız yerleştiriliyor...")
            time.sleep(0.3)
            status_box.update(label="📱 1080x1920 Story kartı oluşturuluyor...")
            
            stats_data = calculate_stats(name, dept, theme_key)
            card_id, card_path = generate_card(photo_bytes, stats_data, session_token=session_token)
            
            # P0: Bir sonraki ziyaretçi için yeni bir oturum token'ı oluştur
            st.session_state["session_token"] = secrets.token_hex(16)
            
            status_box.update(label="✅ Kartınız başarıyla hazırlandı!", state="complete", expanded=False)
            
            base_url = host_choice.rstrip("/")
            download_url = f"{base_url}/kart/{card_id}"
            
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(download_url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            qr_buf = BytesIO()
            qr_img.save(qr_buf, format="PNG")
            
            # Kart ve QR Düzeni
            c_card, c_qr = st.columns([1.2, 1], gap="medium")
            with c_card:
                st.image(card_path, caption=f"{stats_data['name']} • {stats_data['title']}", use_container_width=True)
            
            with c_qr:
                st.markdown('<div class="qr-container">', unsafe_allow_html=True)
                st.markdown("#### 📱 Telefonla Tara")
                st.image(qr_buf.getvalue(), use_container_width=True)
                st.markdown(f"[🔗 Doğrudan Sayfayı Aç]({download_url})")
                
                with open(card_path, "rb") as f:
                    st.download_button(
                        label="💻 Bilgisayara İndir (PNG)",
                        data=f.read(),
                        file_name=f"altinbas_ai_{card_id[:8]}.png",
                        mime="image/png",
                        use_container_width=True
                    )
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.caption("🔒 **Veri Gizliliği Güvencesi:** Bu kart ve ham fotoğraf 5 dakika sonra sunucumuzdan kalıcı olarak silinmektedir.")
    else:
        st.info("👈 Soldaki panelden bilgilerinizi girip fotoğrafınızı yakalayın; karakter kartınız ve indirme QR kodunuz burada anında görünecektir.")

    st.markdown("</div>", unsafe_allow_html=True)
