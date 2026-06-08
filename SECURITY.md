# Security Policy

## Supported versions

FlowQueue is pre-1.0. Security fixes are applied to the latest `main` and the most
recent release. Please run a recent version before reporting.

| Version | Supported |
|---------|-----------|
| latest `main` / latest release | ✅ |
| older releases | ❌ |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report privately to **techdesk@skill.college** (or use GitHub's private
"Report a vulnerability" advisory flow on this repository). Please include:

- A description of the issue and its impact.
- Steps to reproduce (proof-of-concept if available).
- Affected version / commit.

We aim to acknowledge reports within 5 business days and to provide a remediation
timeline after triage. Please give us a reasonable window to release a fix before
public disclosure.

## Scope notes

FlowQueue already hardens several areas — reports against these are especially welcome:

- **SSRF protection** on webhook `endpoint_url` (private / loopback / link-local IPs
  blocked) — `app/core/routing_engine.py` and webhook dispatch.
- **API keys** stored bcrypt-hashed (only a short non-secret prefix is indexed).
- **HMAC-signed** webhook deliveries.
- **JWT** access tokens + httpOnly refresh cookies; multi-tenant isolation per user.
- Deterministic routing rules — **no `eval`**.

When testing, use your own local instance. Do not test against infrastructure you do
not own.
