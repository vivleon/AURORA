import sqlite3
from pathlib import Path

class DB:
    """
    SQLite 데이터베이스 연결을 관리하기 위한 기본 스텁 클래스입니다.
    'app/main.py'에서 이 클래스를 임포트합니다.
    """
    def __init__(self, db_path: str | Path = "data/metrics.db"):
        self.db_path = Path(db_path)
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """
        데이터베이스 파일과 상위 디렉터리가 존재하는지 확인합니다.
        'schema.sql'은 별도로 실행되어야 합니다.
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            print(f"[DB] Database file not found at {self.db_path}. \
Please initialize it using 'schema.sql'.")
            # 최소한의 연결을 위해 빈 파일 생성
            try:
                self.db_path.touch()
            except IOError as e:
                print(f"[ERROR] Could not create db file: {e}")
                
    def connect(self) -> sqlite3.Connection:
        """
        SQLite 데이터베이스 연결을 반환합니다.
        """
        try:
            conn = sqlite3.connect(self.db_path.as_posix())
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            print(f"[ERROR] Failed to connect to database: {e}")
            return None

    # 'bandit.py'의 구버전이 이 함수들을 호출했습니다.
    # 새 Bandit 로직은 이 함수들을 사용하지 않지만, 호환성을 위해 스텁을 남겨둡니다.
    def get_weight(self, context_key: str, tool: str) -> float:
        print(f"[WARN] Deprecated call: get_weight({context_key}, {tool}). Using Bandit-Lite (JSON).")
        return 0.5

    def set_weight(self, context_key: str, tool: str, weight: float):
        print(f"[WARN] Deprecated call: set_weight({context_key}, {tool}). Using Bandit-Lite (JSON).")
        pass