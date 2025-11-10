# CRYPTO PLAN (PQC-Hybrid PoC)


## Today
- TLS 1.3 (X25519/ECDSA), mTLS for internal services.
- Artifact signing (Ed25519) for models and updates.


## PoC Branch (pqc-hybrid)
- **Goal**: hybrid KEM (X25519 + Kyber) for service-to-service.
- **Approach**: run a sidecar reverse-proxy pair with OpenSSL provider supporting PQC; terminate hybrid TLS at the proxy; pass through to FastAPI upstream.


### Layout
```
services/
├─ proxy-a/ (frontend → app A; hybrid TLS listener)
├─ proxy-b/ (frontend → app B; hybrid TLS listener)
└─ certs/ (test CAs, leafs)
```


### Success Criteria
- Handshake completes with classical + PQ KEM.
- App-layer mTLS subject is validated.
- Dashboards show normal latencies; fallback to classical if PQ fails.


## Keys & Rotation
- Short-lived service certs; key rotation on every release cycle.
- Long-term archives encrypted with PQ-safe keys.