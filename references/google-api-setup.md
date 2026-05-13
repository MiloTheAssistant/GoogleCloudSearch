# Google API Setup

Use the Google Cloud Console with organization ID `502896413119` and the Google account `milotheassistant@gmail.com`.

## Enable APIs

In Google Cloud Console, select or create the project that should own the OAuth client, then enable:

- Google Search Console API
- Google Site Verification API

The Search Console API is used for property listing, property creation, sitemap submission, and URL inspection. The Site Verification API is used to generate and verify ownership tokens.

## OAuth Client

Create an OAuth client for an installed/desktop app. Download the client JSON and place it at:

```text
credentials/oauth-client.json
```

Do not commit this file. The repository `.gitignore` excludes `credentials/`, common client-secret filenames, and token caches.

The helper script requests these scopes:

- `https://www.googleapis.com/auth/webmasters`
- `https://www.googleapis.com/auth/siteverification`

The first local authenticated run opens a browser consent flow. Sign in as `milotheassistant@gmail.com`. The refresh token is cached in `.gsc-token.json`, which is also ignored by git.

## Browser Relay Use

Use browser relay only when OAuth consent, Google account selection, or Search Console UI state needs confirmation. The stable automation path is the API script.

## Normal Flow

1. Run `preflight` against the public site URL.
2. Generate a verification token with `get-token`.
3. Place the DNS/file/meta token.
4. Re-run `preflight` with token checks if useful.
5. Run `verify-site`.
6. Run `add-property`.
7. Run `submit-sitemap`.
8. Run `inspect-url`.
