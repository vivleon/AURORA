import hashlib, json, time, os


class AuditLogger:
def __init__(self, path: str):
self.path = path
os.makedirs(os.path.dirname(path), exist_ok=True)
if not os.path.exists(path):
with open(path, 'w', encoding='utf-8') as f: f.write("")


def _last_hash(self):
h = "0"*64
with open(self.path, 'r', encoding='utf-8') as f:
for line in f: h = json.loads(line).get('hash', h)
return h


def record(self, actor: str, action: str, payload: dict):
prev = self._last_hash()
entry = {"ts": time.time(), "actor": actor, "action": action, "payload": payload, "prev": prev}
raw = json.dumps(entry, sort_keys=True).encode()
digest = hashlib.sha256(raw).hexdigest()
entry["hash"] = digest
with open(self.path, 'a', encoding='utf-8') as f:
f.write(json.dumps(entry, ensure_ascii=False) + "\n")
return digest