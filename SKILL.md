---
name: google-search-console
description: Automate Google Search Console website listing workflows from Codex, including property preflight checks, Google Site Verification token handling, Search Console property creation, sitemap submission, and URL Inspection API checks. Use when adding owned websites to Google Search Console, preparing DNS or site verification, or confirming Google indexing visibility.
---

# Google Search Console

Use this skill to list owned websites in Google Search Console with the most automation Google currently supports.

Prefer the hybrid API workflow:

1. Run a public preflight check for the target site.
2. Use Google OAuth for `milotheassistant@gmail.com`.
3. Generate a verification token with the Google Site Verification API.
4. Have the owner place the DNS, file, or meta token.
5. Verify ownership through the API.
6. Add the Search Console property.
7. Submit the sitemap.
8. Inspect the homepage or canonical URL after access exists.

Default to a Domain property (`sc-domain:example.com`) with DNS TXT verification. Fall back to URL-prefix properties (`https://example.com/`) when DNS access is not available or a file/meta token is easier for the hosting setup.

## Tools

The main helper is `scripts/gsc_workflow.py`.

Install dependencies only when API calls are needed:

```powershell
python -m pip install -r scripts/requirements.txt
```

Run credential-free checks:

```powershell
python scripts/gsc_workflow.py preflight https://example.com
python scripts/gsc_workflow.py --help
```

Run authenticated Google workflows:

```powershell
python scripts/gsc_workflow.py list-sites
python scripts/gsc_workflow.py get-token example.com --resource-type INET_DOMAIN --method DNS_TXT
python scripts/gsc_workflow.py verify-site example.com --resource-type INET_DOMAIN --method DNS_TXT
python scripts/gsc_workflow.py add-property sc-domain:example.com
python scripts/gsc_workflow.py submit-sitemap sc-domain:example.com https://example.com/sitemap.xml
python scripts/gsc_workflow.py inspect-url sc-domain:example.com https://example.com/
```

## Credential Handling

Never commit OAuth client secrets or token caches. Keep downloaded OAuth JSON under `credentials/`, which is ignored by git.

Default credential paths:

- OAuth client JSON: `credentials/oauth-client.json`
- Token cache: `.gsc-token.json`

The Google Cloud account context for this workflow is:

- Organization ID: `502896413119`
- Google account: `milotheassistant@gmail.com`

Read `references/google-api-setup.md` when API credentials are missing or OAuth fails. Read `references/verification-methods.md` when choosing or troubleshooting DNS, file, or meta verification.

## Guardrails

- Do not use the Google Indexing API for normal websites; Google limits it to job posting and livestream pages.
- Do not try to bypass Search Console quotas or ownership checks.
- Browser relay is a fallback for consent screens, account confirmation, or UI-only recovery, not the primary automation surface.
- Confirm a token is publicly reachable or visible in DNS before calling `verify-site`.
