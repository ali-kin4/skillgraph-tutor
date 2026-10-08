# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.2.x | Yes |
| < 0.2 | No |

## Reporting a vulnerability

Please report vulnerabilities privately through [GitHub security advisories](https://github.com/ali-kin4/skillgraph-tutor/security/advisories/new). Do not open a public issue.

Include the affected version, a description of the impact, and steps to reproduce. You can expect an acknowledgement within 5 business days and a status update within 14 days. Fixes are released as patch versions and credited in the changelog unless you prefer otherwise.

## Security model

SkillGraph is designed as a **single-user, local** tool.

- The dashboard server binds to `127.0.0.1` only and has **no authentication**. Exposing it on a network or behind a reverse proxy is unsupported.
- Static files are served from a fixed allowlist; there is no directory browsing.
- State-changing requests require `application/json`, a body of at most 8 KB, and a same-origin `Origin` header when one is sent.
- Learner IDs are validated against a strict pattern and symlinked learner files are refused.
- Responses send `Content-Security-Policy` (scripts and styles from self only), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Cache-Control: no-store`.
- CSV exports neutralise spreadsheet formula prefixes.
- The application makes no outbound network requests and collects no telemetry.

The workstation's filesystem permissions are the access-control boundary for learner data.

## In scope

- Bypassing the origin, content-type or size checks on write endpoints
- Path traversal or reading files outside the workspace and asset allowlist
- Script injection through learner names, concept names or other stored data
- CSV/formula injection in exports
- Dependency or supply-chain issues in declared dependencies

## Out of scope

- Attacks that require the server to be deliberately exposed beyond loopback
- Lack of authentication or multi-user isolation (documented design limit)
- Denial of service from a local user who already controls the workstation
