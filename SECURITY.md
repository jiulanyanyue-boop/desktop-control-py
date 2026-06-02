# Security Policy

## Supported versions

This project is pre-1.0. Security fixes target the current `main` branch.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Open a private GitHub
security advisory if available, or contact the repository maintainer through the
owner profile.

Please include:

- Affected version or commit.
- Reproduction steps.
- Expected and actual impact.
- Whether the issue requires an unlocked desktop, browser session, clipboard access, or filesystem access.

## Safety boundaries

`desktop-control-py` controls a local Windows desktop. Treat it as a privileged
local automation server.

The project intentionally does not provide:

- DOM scraping or hidden page text extraction.
- CAPTCHA bypass.
- Job submission automation.
- Browser clipboard scraping.
- Background browser credential extraction.

If a proposed feature crosses one of these boundaries, open a design discussion
before implementation.
