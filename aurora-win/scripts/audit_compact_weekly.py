import os
import sys
import gzip
import shutil
import time
import argparse
import json # (audit_verify.py 수정에 맞게 JSON 임포트 추가)
from pathlib import Path # (Path 객체 사용)
from datetime import datetime, timedelta

def compact_log(log_path: str, archive_dir: str):
    """
    오래된(예: 7일 이상) audit.log 항목을 압축(.gz)하고,
    최신 로그만 남기되 해시체인을 재설정(reseed)합니다.
    (schedule_audit_weekly.xml [cite: vivleon/aurora/AURORA-main/aurora-win/scripts/schedule_audit_weekly.xml]이 호출)
    """
    inp = Path(log_path)
    out_dir = Path(archive_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not inp.exists() or inp.stat().st_size == 0:
        print(f"Log file '{inp}' is empty or does not exist. Nothing to compact.")
        return

    print(f"Compacting log: {inp}")
    
    lines = []
    try:
        lines = [json.loads(l) for l in inp.read_text("utf-8").splitlines() if l.strip()]
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] Failed to read log file: {e}. Aborting compaction.")
        return

    cutoff_ts = (datetime.utcnow() - timedelta(days=7)).timestamp()

    old_lines = [l for l in lines if l.get("ts", 0) < cutoff_ts]
    new_lines = [l for l in lines if l.get("ts", 0) >= cutoff_ts]

    # 1. 오래된 로그 아카이브
    if old_lines:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        archive_name = f"audit-{timestamp}_(compacted).log.gz"
        archive_path = out_dir / archive_name
        
        try:
            with gzip.open(archive_path, "wt", encoding="utf-8") as gz:
                for l in old_lines:
                    gz.write(json.dumps(l, ensure_ascii=False) + "\n")
            print(f"Archived {len(old_lines)} old records to {archive_path}")
        except IOError as e:
            print(f"[ERROR] Failed to write archive: {e}")

    # 2. 새 로그 파일 재작성 (해시체인 재설정)
    print(f"Reseeding hash chain for {len(new_lines)} recent records...")
    
    expected_prev_hash = "0" * 64 # 제네시스 해시
    regenerated_lines = []
    
    for entry in new_lines:
        # 'hash'와 'prev'를 제외한 모든 것을 직렬화
        entry_data_to_hash = entry.copy()
        entry_data_to_hash.pop('hash', None)
        entry_data_to_hash.pop('prev', None)
        
        raw = json.dumps(entry_data_to_hash, sort_keys=True).encode('utf-8')
        recalculated_hash = hashlib.sha256(raw).hexdigest()
        
        # 새 체인 적용
        entry['prev'] = expected_prev_hash
        entry['hash'] = recalculated_hash
        
        regenerated_lines.append(json.dumps(entry, ensure_ascii=False))
        expected_prev_hash = recalculated_hash # 다음 루프를 위해 해시 업데이트

    try:
        # 원본 로그 파일 덮어쓰기
        with open(log_path, 'w', encoding='utf-8') as f:
            if regenerated_lines:
                f.write("\n".join(regenerated_lines) + "\n")
            else:
                f.write("") # 비움
        print(f"Original log file '{log_path}' has been compacted and re-chained.")
    except IOError as e:
        print(f"[ERROR] Failed to write compacted log: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compact and re-chain audit log file.")
    parser.add_argument("--in", dest="input_log", default="data/audit.log", help="Path to the audit.log file (default: data/audit.log)")
    parser.add_argument("--out", dest="output_dir", default="data/archive", help="Directory to save compressed archives (default: data/archive)")
    
    args = parser.parse_args()
    
    compact_log(args.input_log, args.output_dir)