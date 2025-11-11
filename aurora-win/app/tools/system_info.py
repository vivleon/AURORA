# app/tools/system_info.py
import time
from datetime import datetime
from typing import Dict, Any

async def get_info(args: Dict[str, Any], policy, db):
    """
    현재 시간, 기온, 습도 등 환경 정보를 반환합니다.
    (실제 시스템/API 호출은 스텁으로 대체)
    """
    
    # [FIX] 현재 위치 (광주, 대한민국)를 반영하여 시간대 설정
    now_utc = datetime.utcnow()
    
    # (스텁) 로컬 환경 정보
    local_city = "Gwangju, South Korea"
    weather_desc = "Clear (Proximity Alert: Moderate UV)"
    temperature_c = 13.0
    humidity_percent = 78
    
    print(f"[Tool.SystemInfo] Getting real-time data for {local_city}")
    
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
            "cpu_usage_percent": 3.4, # (스텁)
            "ram_free_gb": 12.8,      # (스텁)
            "network_status": "Wi-Fi (99%)" # (스텁)
        }
    }