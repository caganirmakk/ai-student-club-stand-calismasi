import os
import socket
import logging
from typing import List, Tuple

logger = logging.getLogger("network_utils")

def get_candidate_ips() -> List[str]:
    """Sistemdeki aktif ağ arabirimlerinin IPv4 adreslerini tespit eder."""
    ips = set()

    # 1. Stand ortam değişkeni kontrolü
    env_host = os.environ.get("STAND_HOST") or os.environ.get("STAND_IP")
    if env_host:
        return [env_host.strip()]

    # 2. Yerel alt ağlara bağlanma testi (internet gerekmez - gateway veya yerel router)
    probe_targets = [("192.168.1.1", 80), ("192.168.0.1", 80), ("10.0.0.1", 80), ("8.8.8.8", 80)]
    for target_ip, port in probe_targets:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.2)
            s.connect((target_ip, port))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                ips.add(ip)
        except Exception:
            pass

    # 3. Hostname çözümlemesi
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            candidate = info[4][0]
            if candidate and not candidate.startswith("127."):
                ips.add(candidate)
    except Exception:
        pass

    # Sıralama: Özel LAN bloklarını (192.168, 10., 172.) öne al
    sorted_ips = sorted(list(ips), key=lambda x: (not x.startswith("192.168."), not x.startswith("10."), x))
    return sorted_ips if sorted_ips else ["127.0.0.1"]

def get_primary_stand_ip() -> str:
    """Stant QR kodu için en uygun yerel IP adresini döner."""
    candidates = get_candidate_ips()
    return candidates[0] if candidates else "127.0.0.1"

if __name__ == "__main__":
    print("Aday IP'ler:", get_candidate_ips())
    print("Seçilen Stant IP:", get_primary_stand_ip())
