import json
import hashlib
import sys
import os

def verify_hash_chain(log_path: str):
    """
    audit.log 파일의 해시체인 무결성을 검증합니다.
    (schedule_audit_weekly.xml이 호출)
    """
    if not os.path.exists(log_path):
        print(f"Error: Log file not found at {log_path}")
        return False

    print(f"Verifying hash chain for: {log_path}...")
    
    expected_prev_hash = "0" * 64 # 제네시스 해시
    line_number = 0
    is_valid = True

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_number += 1
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    print(f"[FAIL] Line {line_number}: Failed to decode JSON.")
                    is_valid = False
                    continue

                # 1. 'hash' 필드와 'prev' 필드 존재 여부 검사
                if 'hash' not in entry or 'prev' not in entry:
                    print(f"[FAIL] Line {line_number}: Missing 'hash' or 'prev' field.")
                    is_valid = False
                    continue
                
                current_hash = entry['hash']
                prev_hash = entry['prev']

                # 2. 이전 해시 일치 여부 검사
                if prev_hash != expected_prev_hash:
                    print(f"[FAIL] Line {line_number}: Chain broken!")
                    print(f"  Expected prev_hash: {expected_prev_hash}")
                    print(f"  Got prev_hash:      {prev_hash}")
                    is_valid = False
                    # 강제로 체인을 이어가서 추가 오류 검사
                    expected_prev_hash = current_hash
                    continue

                # 3. 현재 해시 무결성 검사
                entry_data_to_hash = entry.copy()
                del entry_data_to_hash['hash']
                
                raw = json.dumps(entry_data_to_hash, sort_keys=True).encode('utf-8')
                recalculated_hash = hashlib.sha256(raw).hexdigest()

                if current_hash != recalculated_hash:
                    print(f"[FAIL] Line {line_number}: Data tampered! Hash mismatch.")
                    print(f"  Recorded hash:    {current_hash}")
                    print(f"  Recalculated hash: {recalculated_hash}")
                    is_valid = False

                # 다음 라인을 위해 예상 해시 업데이트
                expected_prev_hash = current_hash

    except IOError as e:
        print(f"Error reading file: {e}")
        return False

    if is_valid:
        print(f"\n[SUCCESS] Verification complete. All {line_number} entries are valid.")
    else:
        print(f"\n[FAILURE] Verification failed. Integrity compromised.")
        
    return is_valid

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/audit_verify.py <path_to_audit_log>")
        sys.exit(1)
        
    log_file_path = sys.argv[1]
    if not verify_hash_chain(log_file_path):
        sys.exit(1)