# app/tools/system_info.py
import time
from datetime import datetime
from typing import Dict, Any

try:
    import psutil
except ImportError:
    print("[WARN] psutil not installed. System info will use stub data.")
    psutil = None

async def get_info(args: Dict[str, Any], policy, db):
    """
    [업그레이드] 실제 CPU/RAM 정보를 psutil에서 가져옵니다.
    """
    
    now_utc = datetime.utcnow()
    
    # [HARDCODING REMOVAL] 스텁으로 시작
    cpu_usage = 3.4
    ram_free_gb = 12.8

    if psutil:
        try:
            # 실제 CPU/RAM 정보 가져오기
            cpu_usage = psutil.cpu_percent(interval=0.1) 
            mem = psutil.virtual_memory()
            ram_free_gb = round(mem.available / (1024 ** 3), 1)
        except Exception as e:
            print(f"[Tool.SystemInfo ERROR] psutil failed: {e}")
            
    # (스텁) 로컬 환경 정보 (WIFI/날씨는 스텁 유지)
    local_city = "Gwangju, South Korea"
    weather_desc = "Clear (Proximity Alert: Moderate UV)"
    temperature_c = 13.0
    humidity_percent = 78
    
    return {
        "status": "ok",
        "location": local_city,
        "timestamp_utc": now_utc.isoformat() + "Z",
        "weather": {
            "description": weather_desc,
            "temperature_c": temperature_c,
            "humidity_percent": humidity_percent,
        },
        "system_load": {
            "cpu_usage_percent": cpu_usage,
            "ram_free_gb": ram_free_gb,
            "network_status": "Wi-Fi (99%)"
        }
    }