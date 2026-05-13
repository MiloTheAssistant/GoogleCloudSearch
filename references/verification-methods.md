# Verification Methods

Default to domain verification when DNS access is available.

## Domain Property

Search Console property format:

```text
sc-domain:example.com
```

Site Verification API resource:

```text
resource type: INET_DOMAIN
identifier: example.com
method: DNS_TXT
```

The generated token must be added to DNS as a TXT record. DNS propagation can take time. Verify the DNS record is visible before calling `verify-site`.

Use DNS CNAME only when TXT is not available or a registrar workflow requires it.

## URL-Prefix Property

Search Console property format:

```text
https://example.com/
```

Site Verification API resource:

```text
resource type: SITE
identifier: https://example.com/
method: FILE or META
```

Use `FILE` when the site can publish a static verification file at the web root. Use `META` when the site can place a `<meta name="google-site-verification">` tag in the public homepage `<head>`.

For file verification, the file name is the token and the content must be:

```text
google-site-verification: TOKEN
```

For meta verification, place the returned meta tag in the rendered public homepage head.

## Common Failures

- Wrong Google account: OAuth must use the account intended to own the Search Console property.
- Token not public: file or homepage is blocked by auth, middleware, robots, or deployment protection.
- Redirect mismatch: file verification expects the token at the exact root URL.
- DNS not propagated: wait and re-check TXT/CNAME visibility before verifying.
- URL-prefix mismatch: `http`, `https`, `www`, and non-`www` are separate URL-prefix properties.
