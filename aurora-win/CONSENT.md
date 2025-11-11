CONSENT

AURORA is consent-first. Every risky action requires explicit approval.

Types

One-time: "Just this file"

Session: valid until app exit or time-bound (e.g., today)

Persistent: e.g., 30 days for auto-save routine

High-risk: mail to external, system exec, file delete, payments → always explicit

Payload (UI)

Shown to the user:

Purpose (why)

Scope (what + paths)

Risk (low/med/high) + badge

TTL (expiry)

Alternatives (safer options)

Explainability: "Why/How" summary from Planner/Verifier

Audit & Revocation

All requests/decisions are hashed and appended to data/audit.log.

User can revoke persistent consents; expired consents swept by ConsentCollector.

Developer Hooks

Backend gate: planner_consent_gate.evaluate_consent() returns requires_consent for high-risk plans.

Frontend: useConsent().ask(payload) opens modal and posts to /consent/*.