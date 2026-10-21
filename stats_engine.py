import random

MUSE_STATS = [
    {"code": "AUR", "name": "Aura", "min": 86, "max": 99},
    {"code": "STY", "name": "Style Vision", "min": 86, "max": 99},
    {"code": "SPT", "name": "Spotlight", "min": 86, "max": 99},
    {"code": "TRD", "name": "Trend Radar", "min": 86, "max": 99},
    {"code": "SOC", "name": "Social Spark", "min": 86, "max": 99},
    {"code": "GLW", "name": "Prompt Glow", "min": 86, "max": 99},
]

MUSE_TITLES = [
    "Certified Main Character ✨",
    "Aura Icon 🌟",
    "Creative Visionary 🌸",
    "Social Spark Master 💫",
    "Trendsetter 👑",
    "Prompt Alchemist 💎",
    "Style Legend 🎀",
    "Campus Star ✨"
]

PLAYER_STATS = [
    {"code": "KRZ", "name": "Karizma", "min": 86, "max": 99},
    {"code": "VIZ", "name": "Halı Saha Vizyonu", "min": 86, "max": 99},
    {"code": "CLT", "name": "Clutch", "min": 86, "max": 99},
    {"code": "TIQ", "name": "Tech IQ", "min": 86, "max": 99},
    {"code": "CHM", "name": "Squad Chemistry", "min": 86, "max": 99},
    {"code": "DYN", "name": "Dayanıklılık", "min": 86, "max": 99},
]

PLAYER_TITLES = [
    "Halı Saha Maestrosu ⚽",
    "Tech Visionary 💻",
    "Clutch Legend ⚡",
    "Prime Game Changer 🚀",
    "Squad Leader 🛡️",
    "Grandmaster 🧠",
    "Campus MVP 🏆",
    "Limitless Hustler 🔥"
]

PLAYER_POSITIONS = ["CAPTAIN", "MAESTRO", "MVP", "LEADER", "ICON", "PRO"]

def calculate_stats(name: str, department: str = "", theme: str = "player") -> dict:
    theme_normalized = "muse" if theme in ["muse", "it_girl"] else "player"

    if theme_normalized == "muse":
        raw_stats = []
        for item in MUSE_STATS:
            val = random.randint(item["min"], item["max"])
            raw_stats.append({
                "code": item["code"],
                "name": item["name"],
                "value": val
            })
        
        # OVR: En yüksek özelliklerin ortalaması baz alınarak 91-99 aralığında
        top3_avg = sum(sorted([s["value"] for s in raw_stats], reverse=True)[:3]) // 3
        ovr = min(99, max(91, top3_avg + random.randint(0, 2)))
        title = random.choice(MUSE_TITLES)
        position = "MUSE"

    else:
        raw_stats = []
        for item in PLAYER_STATS:
            val = random.randint(item["min"], item["max"])
            raw_stats.append({
                "code": item["code"],
                "name": item["name"],
                "value": val
            })
            
        top3_avg = sum(sorted([s["value"] for s in raw_stats], reverse=True)[:3]) // 3
        ovr = min(99, max(91, top3_avg + random.randint(0, 2)))
        title = random.choice(PLAYER_TITLES)
        position = random.choice(PLAYER_POSITIONS)

    return {
        "name": name.strip().title(),
        "department": department.strip().title() if department else "Altınbaş Üni",
        "theme": theme_normalized,
        "ovr": ovr,
        "title": title,
        "position": position,
        "stats": raw_stats
    }

if __name__ == "__main__":
    import sys
    if sys.stdout:
        sys.stdout.reconfigure(encoding='utf-8')
    test_muse = calculate_stats("Zülal", "Yazılım Müh.", "muse")
    print("Test Muse:", test_muse["ovr"], [s["value"] for s in test_muse["stats"]])
    test_player = calculate_stats("Çağan", "Yazılım Müh.", "player")
    print("Test Player:", test_player["ovr"], [s["value"] for s in test_player["stats"]])
