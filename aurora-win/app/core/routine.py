import yaml
from pathlib import Path
from typing import Dict, Any

# 루틴 정의 파일이 위치할 디렉터리
ROUTINE_DIR = Path("data/routines")

def load_routine_data(routine_name: str) -> Dict[str, Any]:
    """
    data/routines 디렉터리에서 YAML 루틴 파일을 로드하고 파싱합니다.
    (Week 2 목표 - Routine Builder)
    """
    # Directory Traversal 공격 방지
    if ".." in routine_name or "/" in routine_name or "\\" in routine_name:
        raise ValueError("잘못된 루틴 이름 형식입니다.")
    
    p = (ROUTINE_DIR / f"{routine_name}.yml").resolve()
    
    if not p.exists():
        # .yaml을 폴백(fallback)으로 시도
        p = (ROUTINE_DIR / f"{routine_name}.yaml").resolve()
        if not p.exists():
            raise FileNotFoundError(f"루틴 파일을 찾을 수 없습니다: '{routine_name}'")

    # 보안 검사: 파일이 의도된 디렉터리 내에 있는지 확인
    if ROUTINE_DIR.resolve() not in p.parents:
        raise PermissionError("루틴 경로가 허용된 디렉터리 외부에 있습니다.")
        
    print(f"[Routine] 루틴 로드 중: {p}")
    with open(p, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)