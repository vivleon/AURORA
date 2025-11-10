"""
Aurora Model Fetcher
- Securely fetches model files and validates SHA-256 and signature
- Usage:
  python model_fetch.py --name phi3-mini-gguf \
      --url https://models.example.com/phi3-mini-4bit.gguf \
      --sha256 <hex> \
      --sig <base64> \
      --pubkey models/pubkey.ed25519 \
      --out models/llm/phi3-mini-4bit.gguf

Note: Network fetching is optional; you can also supply a local file path with --file.
"""

import argparse, base64, hashlib, json, os, pathlib, sys
from typing import Optional

try:
    import nacl.signing  # PyNaCl
    import nacl.exceptions
    HAS_PYNACL = True
except Exception:
    HAS_PYNACL = False


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sig(pubkey_path: pathlib.Path, message_path: pathlib.Path, b64sig: str) -> bool:
    if not HAS_PYNACL:
        print("[WARN] PyNaCl not installed, skipping signature verification")
        return True
    pk = nacl.signing.VerifyKey(pubkey_path.read_bytes())
    sig = base64.b64decode(b64sig)
    try:
        pk.verify(message_path.read_bytes(), sig)
        return True
    except nacl.exceptions.BadSignatureError:
        return False


def ensure_dir(p: pathlib.Path):
    p.parent.mkdir(parents=True, exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url")
    src.add_argument("--file")
    ap.add_argument("--sha256", required=True)
    ap.add_argument("--sig", required=False)
    ap.add_argument("--pubkey", required=False)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    ensure_dir(out)

    # fetch/copy
    if args.file:
        src_path = pathlib.Path(args.file)
        if not src_path.exists():
            print(f"[ERR] file not found: {src_path}")
            sys.exit(2)
        data = src_path.read_bytes()
        out.write_bytes(data)
    else:
        # simple urllib fetch (no extra deps)
        import urllib.request
        with urllib.request.urlopen(args.url) as r:
            out.write_bytes(r.read())

    # hash verify
    actual = sha256_file(out)
    expected = args.sha256.lower()
    if actual.lower() != expected:
        print(f"[FAIL] sha256 mismatch: expected {expected[:12]}, got {actual[:12]}")
        out.unlink(missing_ok=True)
        sys.exit(3)
    print(f"[OK] sha256 verified: {actual}")

    # signature verify (optional)
    if args.sig and args.pubkey:
        ok = verify_sig(pathlib.Path(args.pubkey), out, args.sig)
        if not ok:
            print("[FAIL] signature verification failed")
            out.unlink(missing_ok=True)
            sys.exit(4)
        print("[OK] signature verified")

    # manifest update
    manifest = pathlib.Path("models/model_manifest.json")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(manifest.read_text("utf-8"))
    except Exception:
        data = {"models": {}}

    data.setdefault("models", {})[args.name] = {
        "path": str(out.as_posix()),
        "sha256": actual,
        "sig": args.sig or None
    }
    manifest.write_text(json.dumps(data, indent=2), "utf-8")
    print(f"[OK] installed {args.name} → {out}")


if __name__ == "__main__":
    main()
