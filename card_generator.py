import os
import secrets
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CARDS_DIR = os.path.join(os.path.dirname(__file__), "static", "cards")
SNAPS_DIR = os.path.join(os.path.dirname(__file__), "static", "snaps")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
FRAMES_DIR = os.path.join(ASSETS_DIR, "frames")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

FRAME_MUSE_PATH = os.path.join(FRAMES_DIR, "frame_muse.jpg")
FRAME_APEX_PATH = os.path.join(FRAMES_DIR, "frame_apex.jpg")

os.makedirs(CARDS_DIR, exist_ok=True)
os.makedirs(SNAPS_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

REMBG_SESSION = None
REMBG_AVAILABLE = False

try:
    import rembg
    REMBG_SESSION = rembg.new_session("u2netp")
    REMBG_AVAILABLE = True
except Exception:
    REMBG_AVAILABLE = False

def process_photo_portrait(photo: Image.Image, target_w: int, target_h: int, theme: str = "player") -> Image.Image:
    """
    Portre fotoğrafını işler:
    1. rembg (u2netp) ile 0.2 saniyede arka planı şeffaflaştırır ve neon aura ekler.
    2. rembg yoksa/hata verirse: Sinematik radyal blur ve tema aurası uygular.
    """
    photo = photo.convert("RGBA")
    
    # 1. Hedef en-boy oranına göre kırp ve ölçekle
    aspect = photo.height / photo.width
    target_aspect = target_h / target_w
    if aspect > target_aspect:
        tw = target_w
        th = int(target_w * aspect)
    else:
        th = target_h
        tw = int(target_h / aspect)
    photo_scaled = photo.resize((tw, th), Image.Resampling.LANCZOS)
    cx = (tw - target_w) // 2
    cy = (th - target_h) // 2
    cropped = photo_scaled.crop((cx, cy, cx + target_w, cy + target_h))

    # 2. rembg ile arka planı ayır
    if REMBG_AVAILABLE and REMBG_SESSION:
        try:
            segmented = rembg.remove(cropped, session=REMBG_SESSION)
            # Arka plan başarılıysa, portre arkasına hafif neon derinlik aurası ekle
            bg_glow = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            draw_g = ImageDraw.Draw(bg_glow)
            glow_color = (236, 72, 153, 50) if theme == "muse" else (0, 200, 255, 50)
            draw_g.ellipse([target_w * 0.1, target_h * 0.15, target_w * 0.9, target_h * 0.85], fill=glow_color)
            bg_glow = bg_glow.filter(ImageFilter.GaussianBlur(35))
            
            combined = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            combined.paste(bg_glow, (0, 0), bg_glow)
            combined.paste(segmented, (0, 0), segmented)
            return combined
        except Exception:
            pass

    # 3. Yüksek Kaliteli Sinematik Yumuşatma Fallback'i:
    # Odanın/perdenin sert hatlarını eritip odaklı stüdyo portresine dönüştürür
    vignette_mask = Image.new("L", (target_w, target_h), 0)
    v_draw = ImageDraw.Draw(vignette_mask)
    v_draw.ellipse([15, 15, target_w - 15, target_h - 15], fill=255)
    vignette_mask = vignette_mask.filter(ImageFilter.GaussianBlur(25))

    blurred_bg = cropped.filter(ImageFilter.GaussianBlur(35))
    tint = Image.new("RGBA", (target_w, target_h), (90, 30, 60, 110) if theme == "muse" else (10, 35, 70, 120))
    blurred_bg = Image.alpha_composite(blurred_bg.convert("RGBA"), tint)

    final_portrait = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    final_portrait.paste(blurred_bg, (0, 0))
    final_portrait.paste(cropped, (0, 0), vignette_mask)
    return final_portrait

MONTSERRAT_PATH = os.path.join(FONTS_DIR, "Montserrat-Bold.ttf")
BEBAS_PATH = os.path.join(FONTS_DIR, "BebasNeue-Regular.ttf")

def get_font(size: int, bold: bool = True, family: str = "montserrat") -> ImageFont.FreeTypeFont:
    """Tasarım şablonuna özel modern ve dikkat çekici fontları yükler."""
    if family == "montserrat" and os.path.exists(MONTSERRAT_PATH):
        try:
            f = ImageFont.truetype(MONTSERRAT_PATH, size)
            if hasattr(f, "set_variation_by_name"):
                f.set_variation_by_name("ExtraBold" if bold else "SemiBold")
            return f
        except Exception:
            pass
    elif family == "bebas" and os.path.exists(BEBAS_PATH):
        try:
            return ImageFont.truetype(BEBAS_PATH, size)
        except Exception:
            pass

    # Yüksek kaliteli sistem fontları (Bahnschrift / Segoe UI / Arial)
    candidates = [
        "C:\\Windows\\Fonts\\bahnschrift.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def get_fitted_font(text: str, max_w: int, max_size: int = 26, min_size: int = 14, bold: bool = True, family: str = "montserrat") -> ImageFont.FreeTypeFont:
    for s in range(max_size, min_size - 1, -1):
        f = get_font(s, bold=bold, family=family)
        try:
            w = f.getlength(text)
        except Exception:
            w = len(text) * (s * 0.6)
        if w <= max_w:
            return f
    return get_font(min_size, bold=bold, family=family)

def clean_label(text: str) -> str:
    return text.replace("✨", "").replace("💅", "").replace("🔍", "").replace("👗", "") \
               .replace("🔮", "").replace("🧸", "").replace("⚡", "").replace("⚽", "") \
               .replace("🎮", "").replace("💻", "").replace("☕", "").replace("🔋", "") \
               .replace("👑", "").replace("🎀", "").replace("🌸", "").replace("🚀", "") \
               .replace("🕹️", "").replace("🌟", "").replace("💫", "").replace("🛡️", "") \
               .replace("🏆", "").replace("💎", "").replace("🧠", "").strip()

def create_muse_card_from_template(photo: Image.Image, stats_data: dict) -> Image.Image:
    """Tam 1080x1920 Instagram Story ölçüsünde Muse Edition kartı oluşturur."""
    W, H = 1080, 1920
    
    if os.path.exists(FRAME_MUSE_PATH):
        bg = Image.open(FRAME_MUSE_PATH).resize((W, H), Image.Resampling.LANCZOS).convert("RGBA")
    else:
        bg = Image.new("RGBA", (W, H), (30, 20, 35, 255))

    # 1. Portre Yerleşimi [244, 255, 836, 1015] (W: 592, H: 760)
    pw, ph = 592, 760
    processed_portrait = process_photo_portrait(photo, pw, ph, theme="muse")

    mask = Image.new("L", (pw, ph), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([8, 8, pw - 8, ph - 8], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(8))

    photo_container = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    photo_container.paste(processed_portrait, (0, 0), mask)
    bg.paste(photo_container, (244, 255), photo_container)

    # 2. Tipografi ve Metinler (Montserrat ExtraBold Luxury Tipografi)
    draw = ImageDraw.Draw(bg)
    font_header = get_font(28, bold=True, family="montserrat")
    font_sub_header = get_font(17, bold=True, family="montserrat")
    font_ovr = get_font(68, bold=True, family="montserrat")
    font_lbl = get_font(22, bold=True, family="montserrat")
    font_score = get_font(32, bold=True, family="montserrat")

    # Üst Ortak Kulüp Başlığı
    draw.text((540, 140), "ALTINBAŞ UNIVERSITY AI CLUB", font=font_header, fill=(215, 145, 160), anchor="mm")
    draw.text((540, 178), "MUSE EDITION • ORYANTASYON 2026", font=font_sub_header, fill=(185, 120, 135), anchor="mm")

    # Sol Üst OVR Puanı
    ovr_val = str(stats_data.get("ovr", 97))
    draw.text((180, 312), ovr_val, font=font_ovr, fill=(195, 120, 135), anchor="mm")

    # 3. İstatistikler & Puanlar (Kutulara ve sağ halkalara milimetrik oturan koordinatlar)
    stats_list = stats_data.get("stats", [])
    stats_left = stats_list[:3]
    stats_right = stats_list[3:6]
    y_rows = [1180, 1359, 1537]

    for i in range(min(3, len(stats_left))):
        y = y_rows[i]
        s_l = stats_left[i]
        lbl_l = clean_label(s_l["name"]).upper()
        # Sol kutu etiketi ve halkadaki puanı (X=506)
        draw.text((145, y), lbl_l, font=font_lbl, fill=(130, 60, 85), anchor="lm")
        draw.text((506, y), str(s_l["value"]), font=font_score, fill=(195, 65, 105), anchor="mm")

        if i < len(stats_right):
            s_r = stats_right[i]
            lbl_r = clean_label(s_r["name"]).upper()
            # Sağ kutu etiketi ve halkadaki puanı (X=945)
            draw.text((580, y), lbl_r, font=font_lbl, fill=(130, 60, 85), anchor="lm")
            draw.text((945, y), str(s_r["value"]), font=font_score, fill=(195, 65, 105), anchor="mm")

    # 4. İsim ve Unvan (Kalıba Milimetrik Oturan Kapsül Koordinatları)
    name_str = stats_data.get("name", "Misafir").upper()
    dept_str = stats_data.get("department", "Altınbaş Üni").upper()
    title_str = clean_label(stats_data.get("title", "Aura Icon")).upper()

    # İsim: Tam ortadaki büyük cam kapsülün merkezinde (Y = 1708)
    fit_name_f = get_fitted_font(name_str, max_w=760, max_size=52, min_size=32, bold=True, family="montserrat")
    draw.text((540, 1708), name_str, font=fit_name_f, fill=(145, 50, 75), anchor="mm")

    # Bölüm & Unvan: Altındaki küçük cam kapsülün merkezinde (Y = 1792)
    sub_text = f"{dept_str} • {title_str}"
    fit_sub_f = get_fitted_font(sub_text, max_w=460, max_size=17, min_size=12, bold=True, family="montserrat")
    draw.text((540, 1792), sub_text, font=fit_sub_f, fill=(175, 85, 110), anchor="mm")

    return bg

    return bg

def create_player_card_from_template(photo: Image.Image, stats_data: dict) -> Image.Image:
    """Tam 1080x1920 Instagram Story ölçüsünde Player Card • Football Edition oluşturur."""
    W, H = 1080, 1920
    
    if os.path.exists(FRAME_APEX_PATH):
        bg = Image.open(FRAME_APEX_PATH).resize((W, H), Image.Resampling.LANCZOS).convert("RGBA")
    else:
        bg = Image.new("RGBA", (W, H), (15, 20, 30, 255))

    # 1. Kalkan Çerçevesine Portre [265, 375, 815, 1045] (W: 550, H: 670)
    pw, ph = 550, 670
    processed_portrait = process_photo_portrait(photo, pw, ph, theme="player")

    mask = Image.new("L", (pw, ph), 0)
    mask_draw = ImageDraw.Draw(mask)
    pts_rel = [(10, 10), (pw - 10, 10), (pw - 10, int(ph * 0.65)), (int(pw * 0.5), ph - 10), (10, int(ph * 0.65))]
    mask_draw.polygon(pts_rel, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(8))

    photo_container = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    photo_container.paste(processed_portrait, (0, 0), mask)
    bg.paste(photo_container, (265, 375), photo_container)

    # 2. Tipografi ve Yazılar (Bebas / Bahnschrift Atletik Spor Tipografisi)
    draw = ImageDraw.Draw(bg)
    font_header = get_font(30, bold=True, family="bebas")
    font_sub_header = get_font(20, bold=True, family="bebas")
    font_ovr = get_font(72, bold=True, family="bebas")
    font_lbl = get_font(24, bold=True, family="montserrat")
    font_score = get_font(38, bold=True, family="bebas")

    # Üst Başlık (Kulüp & Futbol Kimliği)
    draw.text((540, 130), "ALTINBAŞ UNIVERSITY AI CLUB", font=font_header, fill=(240, 245, 255), anchor="mm")
    draw.text((540, 168), "PLAYER CARD • FOOTBALL EDITION", font=font_sub_header, fill=(0, 240, 255), anchor="mm")

    # Sol Üst OVR Puanı
    ovr_val = str(stats_data.get("ovr", 97))
    draw.text((168, 175), ovr_val, font=font_ovr, fill=(255, 255, 255), anchor="mm")

    # 3. İstatistikler & Puanlar (Kutulara ve neon karelere tam oturan koordinatlar)
    stats_list = stats_data.get("stats", [])
    stats_left = stats_list[:3]
    stats_right = stats_list[3:6]
    y_rows = [1174, 1340, 1506]

    for i in range(min(3, len(stats_left))):
        y = y_rows[i]
        s_l = stats_left[i]
        lbl_l = clean_label(s_l["name"]).upper()
        draw.text((110, y), lbl_l, font=font_lbl, fill=(205, 225, 245), anchor="lm")
        draw.text((450, y), str(s_l["value"]), font=font_score, fill=(0, 245, 255), anchor="mm")

        if i < len(stats_right):
            s_r = stats_right[i]
            lbl_r = clean_label(s_r["name"]).upper()
            draw.text((600, y), lbl_r, font=font_lbl, fill=(205, 225, 245), anchor="lm")
            draw.text((940, y), str(s_r["value"]), font=font_score, fill=(0, 245, 255), anchor="mm")

    # 4. İsim ve Unvan (Kutularına Tam Oturan Koordinatlar)
    name_str = stats_data.get("name", "Karakter").upper()
    dept_str = stats_data.get("department", "Altınbaş Üni").upper()
    title_str = clean_label(stats_data.get("title", "Kampüs Efsanesi")).upper()

    fit_name_f = get_fitted_font(name_str, max_w=820, max_size=56, min_size=32, bold=True, family="montserrat")
    draw.text((540, 1695), name_str, font=fit_name_f, fill=(255, 255, 255), anchor="mm")

    sub_text_player = f"{dept_str} • {title_str}"
    fit_sub_f = get_fitted_font(sub_text_player, max_w=560, max_size=20, min_size=13, bold=True, family="montserrat")
    draw.text((540, 1805), sub_text_player, font=fit_sub_f, fill=(90, 210, 255), anchor="mm")

    return bg

# İsim eşleştirmeleri ve geriye dönük uyumluluk
create_apex_card_from_template = create_player_card_from_template
create_it_girl_card = create_muse_card_from_template
create_fut_card = create_player_card_from_template

def generate_card(photo_bytes: bytes, stats_data: dict, session_token: str = None) -> tuple[str, str]:
    """
    Fotoğraf ve istatistikleri alır, tam 1080x1920 Story kartı üretir,
    128-bit rastgele token ile PNG olarak kaydeder, ham fotoğrafı güvenle siler.
    """
    input_image = Image.open(BytesIO(photo_bytes))
    theme = stats_data.get("theme", "player")

    if theme in ["muse", "it_girl"]:
        final_card = create_muse_card_from_template(input_image, stats_data)
    else:
        final_card = create_player_card_from_template(input_image, stats_data)

    # P0: Tahmin edilemez 128-bit kriptografik rastgele kart ID'si (32 karakter hex)
    card_id = secrets.token_hex(16)
    out_path = os.path.join(CARDS_DIR, f"{card_id}.png")
    final_card.save(out_path, format="PNG", quality=95)

    # P0: Ham fotoğrafı kart üretiminden hemen sonra sil (KVKK güvencesi)
    if session_token:
        snap_path = os.path.join(SNAPS_DIR, f"{session_token}.png")
        if os.path.exists(snap_path):
            try:
                os.remove(snap_path)
            except Exception:
                pass

    return card_id, out_path

if __name__ == "__main__":
    from stats_engine import calculate_stats
    dummy_photo = Image.new("RGB", (640, 480), (120, 150, 180))
    buf = BytesIO()
    dummy_photo.save(buf, format="PNG")
    b = buf.getvalue()

    s_m = calculate_stats("Selin Kaya", "Endüstri Müh.", "muse")
    cid_m, path_m = generate_card(b, s_m)
    print("Muse Generated:", cid_m, Image.open(path_m).size)

    s_p = calculate_stats("Çağan Demir", "Yazılım Müh.", "player")
    cid_p, path_p = generate_card(b, s_p)
    print("Player Generated:", cid_p, Image.open(path_p).size)
