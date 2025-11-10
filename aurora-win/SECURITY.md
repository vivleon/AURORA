# SECURITY


## Threat Model (high level)
- **RCE / Privilege Escalation / Local Token Theft**
- **Data exfiltration** from lost device or malware
- **MITM / Session hijacking** between local services
- **Supply chain** (deps, updates, plugins)
- **Model security** (poisoning, exfiltration, theft)
- **Insider & credential abuse**
- **Future cryptanalysis** (post-quantum)


## Defense-in-Depth
1. **Hardware root of trust**: TPM 2.0 / Secure Boot / measured boot (attestable).
2. **Disk & key sealing**: OS full-disk encryption; keys sealed to TPM.
3. **Network**: TLS 1.3 everywhere; mTLS for service↔service. PQC-hybrid PoC branch.
4. **Least privilege**: tools/plugins sandboxed; allowlist scopes via `policy.json`.
5. **Signed execution**: signed PowerShell under `scripts/signed_ps/` only; updates signed.
6. **Observability**: immutable audit (`data/audit.log` + hash chain), metrics in `data/metrics.db`.
7. **Automated response**: weekly audit integrity check + compact; anomaly triggers rollback.


## Secure Development
- SAST/DAST/SCA in CI; dependency pinning; reproducible builds.
- Code signing for artifacts; staged rollout with auto-rollback on anomaly.


## Incident Response (IR)
- **Detect**: dashboards (errors, consent, high-risk), weekly integrity job.
- **Contain**: revoke risky scopes, disable tools, roll back last update.
- **Eradicate**: rotate keys; patch and re-sign; verify devices by attestation.
- **Recover**: restore from trusted snapshot; re-enable scopes gradually.
- **Postmortem**: timeline from audit log; add regression tests.


## KPIs
- MTTD / MTTR, failed-authorization rate, exploit-attempts, p95 latency (per tool), consent decline rate.