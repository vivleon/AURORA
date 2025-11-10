"""
Merge/ensure high-risk rules into data/policy.json.
Usage: python scripts/policy_merge.py --file data/policy.json
"""
import json, argparse, sys


WANTED = [
"payment.*", "os.settings", "update.apply", "mail.send", "system.exec.limited", "files.delete"
]


def main(path: str):
try:
with open(path, "r", encoding="utf-8") as f:
data = json.load(f)
except FileNotFoundError:
data = {"policy_version":"1.1","risk_rules":{}}


rr = data.setdefault("risk_rules", {})
cur = set(rr.get("high_risk", []))
cur.update(WANTED)
rr["high_risk"] = sorted(cur)
rr.setdefault("require_consent_each_time", True)


with open(path, "w", encoding="utf-8") as f:
json.dump(data, f, ensure_ascii=False, indent=2)
print(f"updated {path}")


if __name__ == "__main__":
ap = argparse.ArgumentParser()
ap.add_argument("--file", default="data/policy.json")
args = ap.parse_args()
main(args.file)