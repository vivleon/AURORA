import json

class Policy:
    def __init__(self, data):
        self.data = data
        self.require_each_time = data.get("consent", {}).get("require_each_time", True)

    @classmethod
    def from_file(cls, path):
        return cls(json.load(open(path, 'r', encoding='utf-8')))

    def allowed(self, scope: str) -> bool:
        s = self.data.get("scopes", {}).get(scope)
        return bool(s and s.get("allow"))
