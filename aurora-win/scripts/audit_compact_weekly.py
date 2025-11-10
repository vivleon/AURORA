import os
import sys
import gzip
import shutil
import time
import argparse

def compact_log(log_path: str, archive_dir: str):
    """
    오래된 audit.log 파일을 압축(.gz)하고 원본 로그를 삭제(초기화)합니다.
    (schedule_audit_weekly.xml이 호출)
    """
    if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
        print(f"Log file '{log_path}' is empty or does not exist. Nothing to compact.")
        return

    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir, exist_ok=True)
        print(f"Created archive directory: {archive_dir}")

    # 1. 압축 파일 이름 생성 (예: audit-20251110-144200.log.gz)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    archive_name = f"audit-{timestamp}.log.gz"
    archive_path = os.path.join(archive_dir, archive_name)

    print(f"Compacting '{log_path}' to '{archive_path}'...")

    try:
        # 2. 파일을 Gzip으로 압축
        with open(log_path, 'rb') as f_in:
            with gzip.open(archive_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        print(f"Compaction successful.")

        # 3. 원본 로그 파일 초기화 (삭제)
        # 중요: 이 작업은 audit_verify.py가 성공한 후에만 실행되어야 합니다.
        # (실제 운영 시에는 XML 스케줄러에서 순서를 보장해야 함)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("")
        print(f"Original log file '{log_path}' has been cleared.")

    except (IOError, OSError) as e:
        print(f"Error during compaction: {e}")
        print("Original log file was NOT cleared.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compact audit log file.")
    parser.add_argument("--in", dest="input_log", required=True, help="Path to the audit.log file")
    parser.add_argument("--out", dest="output_dir", required=True, help="Directory to save compressed archives")
    
    args = parser.parse_args()
    
    compact_log(args.input_log, args.output_dir)