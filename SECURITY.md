# Security

Least privilege, explicit service identities, no secrets in source control, encryption in transit/at rest, immutable audit events, dependency/container scanning, provider-license enforcement, and data isolation where required.

AI output is untrusted until validated. Models use an allow-listed tool layer; generated claims cannot become authoritative observations without deterministic validation and provenance.

## Analyst API production boundary

The analyst API is read-only but still must not be directly exposed to an untrusted network. Production deployments should terminate TLS and enforce OAuth/OIDC authentication, least-privilege authorization, rate limiting, and gateway logging before forwarding to the runtime. The service supports a deployment-controlled bearer-token boundary for isolated environments, but a single static token is not a substitute for an identity-aware gateway. Direct backend access should be denied by network policy. This follows OWASP guidance to centralize authorization while retaining service-level checks.