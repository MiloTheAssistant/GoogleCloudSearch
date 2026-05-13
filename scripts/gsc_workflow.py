#!/usr/bin/env python3
"""Google Search Console listing workflow helper."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_CREDENTIALS = Path("credentials/oauth-client.json")
DEFAULT_TOKEN = Path(".gsc-token.json")
SCOPES = [
    "https://www.googleapis.com/auth/webmasters",
    "https://www.googleapis.com/auth/siteverification",
]


class HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_head = False
        self.title = ""
        self.canonical = ""
        self.meta_verification = ""
        self.robots_meta = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "head":
            self.in_head = True
        if not self.in_head:
            return
        if tag.lower() == "link" and attrs_dict.get("rel", "").lower() == "canonical":
            self.canonical = attrs_dict.get("href", "")
        if tag.lower() == "meta":
            name = attrs_dict.get("name", "").lower()
            if name == "google-site-verification":
                self.meta_verification = attrs_dict.get("content", "")
            if name == "robots":
                self.robots_meta = attrs_dict.get("content", "")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "head":
            self.in_head = False

    def handle_data(self, data: str) -> None:
        # Title extraction is intentionally minimal; preflight does not need full DOM parsing.
        if self.in_head and not self.title and data.strip():
            self.title = data.strip()


def fetch_url(url: str, timeout: int = 20) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "Codex-GoogleSearchConsoleSkill/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(2_500_000)
            return {
                "ok": True,
                "url": response.geturl(),
                "status": response.status,
                "content_type": response.headers.get("content-type", ""),
                "body": body.decode("utf-8", errors="replace"),
            }
    except HTTPError as exc:
        body = exc.read(250_000).decode("utf-8", errors="replace")
        return {
            "ok": False,
            "url": url,
            "status": exc.code,
            "content_type": exc.headers.get("content-type", ""),
            "body": body,
            "error": str(exc),
        }
    except URLError as exc:
        return {"ok": False, "url": url, "status": None, "body": "", "error": str(exc)}


def normalize_site_url(url: str) -> str:
    parsed = urlparse(url if re.match(r"^https?://", url) else f"https://{url}")
    if not parsed.netloc:
        raise ValueError(f"Invalid site URL: {url}")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"


def default_domain(url: str) -> str:
    parsed = urlparse(normalize_site_url(url))
    host = parsed.netloc.split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def preflight(args: argparse.Namespace) -> int:
    site_url = normalize_site_url(args.url)
    root = f"{urlparse(site_url).scheme}://{urlparse(site_url).netloc}/"
    homepage = fetch_url(site_url)
    robots = fetch_url(urljoin(root, "robots.txt"))
    sitemap_url = args.sitemap or urljoin(root, "sitemap.xml")
    sitemap = fetch_url(sitemap_url)

    parser = HeadParser()
    if homepage.get("body"):
        parser.feed(homepage["body"])

    result: dict[str, Any] = {
        "site_url": site_url,
        "domain_property": f"sc-domain:{default_domain(site_url)}",
        "url_prefix_property": root,
        "homepage": {
            "ok": homepage["ok"],
            "status": homepage["status"],
            "final_url": homepage["url"],
            "content_type": homepage.get("content_type", ""),
            "canonical": parser.canonical,
            "robots_meta": parser.robots_meta,
            "has_google_site_verification_meta": bool(parser.meta_verification),
        },
        "robots_txt": {
            "ok": robots["ok"],
            "status": robots["status"],
            "url": urljoin(root, "robots.txt"),
            "mentions_sitemap": "sitemap:" in robots.get("body", "").lower(),
        },
        "sitemap": {
            "ok": sitemap["ok"],
            "status": sitemap["status"],
            "url": sitemap_url,
            "looks_like_xml": "<urlset" in sitemap.get("body", "") or "<sitemapindex" in sitemap.get("body", ""),
        },
        "recommendation": "Use domain property with DNS_TXT verification when DNS access is available.",
    }

    if args.verification_file:
        verification_url = urljoin(root, args.verification_file)
        verification = fetch_url(verification_url)
        result["verification_file"] = {
            "ok": verification["ok"],
            "status": verification["status"],
            "url": verification_url,
            "contains_google_site_verification": "google-site-verification:" in verification.get("body", ""),
        }

    print_json(result)
    return 0 if homepage["ok"] else 1


def require_google_libs() -> Any:
    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise SystemExit(
            "Missing Google API dependencies. Run: python -m pip install -r scripts/requirements.txt"
        ) from exc
    return GoogleAuthRequest, Credentials, InstalledAppFlow, build


def credentials(args: argparse.Namespace) -> Any:
    GoogleAuthRequest, Credentials, InstalledAppFlow, _build = require_google_libs()
    token_path = Path(args.token)
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(GoogleAuthRequest())
    else:
        credentials_path = Path(args.credentials)
        if not credentials_path.exists():
            raise SystemExit(f"OAuth client JSON not found: {credentials_path}")
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_service(args: argparse.Namespace, api: str, version: str) -> Any:
    _req, _creds_cls, _flow, build = require_google_libs()
    return build(api, version, credentials=credentials(args), cache_discovery=False)


def list_sites(args: argparse.Namespace) -> int:
    service = build_service(args, "searchconsole", "v1")
    print_json(service.sites().list().execute())
    return 0


def get_token(args: argparse.Namespace) -> int:
    service = build_service(args, "siteVerification", "v1")
    body = {
        "site": {"type": args.resource_type, "identifier": args.identifier},
        "verificationMethod": args.method,
    }
    response = service.webResource().getToken(body=body).execute()
    print_json(
        {
            "request": body,
            "response": response,
            "placement": placement_instructions(args.resource_type, args.identifier, response),
        }
    )
    return 0


def verify_site(args: argparse.Namespace) -> int:
    service = build_service(args, "siteVerification", "v1")
    body = {"site": {"type": args.resource_type, "identifier": args.identifier}}
    response = service.webResource().insert(verificationMethod=args.method, body=body).execute()
    print_json(response)
    return 0


def add_property(args: argparse.Namespace) -> int:
    service = build_service(args, "searchconsole", "v1")
    response = service.sites().add(siteUrl=args.property).execute()
    print_json({"property": args.property, "response": response or {}})
    return 0


def submit_sitemap(args: argparse.Namespace) -> int:
    service = build_service(args, "searchconsole", "v1")
    response = service.sitemaps().submit(siteUrl=args.property, feedpath=args.sitemap).execute()
    print_json({"property": args.property, "sitemap": args.sitemap, "response": response or {}})
    return 0


def inspect_url(args: argparse.Namespace) -> int:
    service = build_service(args, "searchconsole", "v1")
    body = {
        "siteUrl": args.property,
        "inspectionUrl": args.url,
        "languageCode": args.language_code,
    }
    response = service.urlInspection().index().inspect(body=body).execute()
    print_json(response)
    return 0


def placement_instructions(resource_type: str, identifier: str, response: dict[str, Any]) -> dict[str, Any]:
    method = response.get("method", "")
    token = response.get("token", "")
    if method == "DNS_TXT":
        return {"type": "dns_txt", "host": identifier, "value": token}
    if method == "DNS_CNAME":
        parts = token.split()
        return {"type": "dns_cname", "name": parts[0] if parts else "", "value": parts[1] if len(parts) > 1 else ""}
    if method == "FILE":
        return {
            "type": "file",
            "path": f"/{token}",
            "content": f"google-site-verification: {token}",
        }
    if method == "META":
        return {"type": "meta", "tag": token, "location": "public homepage <head>"}
    return {"type": method.lower(), "token": token, "resource_type": resource_type, "identifier": identifier}


def add_common_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--credentials", default=str(DEFAULT_CREDENTIALS), help="OAuth installed-app client JSON path")
    parser.add_argument("--token", default=str(DEFAULT_TOKEN), help="OAuth token cache path")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Google Search Console listing workflow helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight_parser = subparsers.add_parser("preflight", help="Check public SEO/Search Console readiness")
    preflight_parser.add_argument("url", help="Public site URL")
    preflight_parser.add_argument("--sitemap", help="Explicit sitemap URL")
    preflight_parser.add_argument("--verification-file", help="Google verification file name to check at site root")
    preflight_parser.set_defaults(func=preflight)

    list_parser = subparsers.add_parser("list-sites", help="List Search Console properties")
    add_common_auth_args(list_parser)
    list_parser.set_defaults(func=list_sites)

    token_parser = subparsers.add_parser("get-token", help="Generate a Site Verification token")
    add_common_auth_args(token_parser)
    token_parser.add_argument("identifier", help="Domain name for INET_DOMAIN or URL for SITE")
    token_parser.add_argument("--resource-type", choices=["INET_DOMAIN", "SITE"], default="INET_DOMAIN")
    token_parser.add_argument(
        "--method",
        choices=["DNS_TXT", "DNS_CNAME", "FILE", "META", "ANALYTICS", "TAG_MANAGER"],
        default="DNS_TXT",
    )
    token_parser.set_defaults(func=get_token)

    verify_parser = subparsers.add_parser("verify-site", help="Verify ownership after token placement")
    add_common_auth_args(verify_parser)
    verify_parser.add_argument("identifier", help="Domain name for INET_DOMAIN or URL for SITE")
    verify_parser.add_argument("--resource-type", choices=["INET_DOMAIN", "SITE"], default="INET_DOMAIN")
    verify_parser.add_argument(
        "--method",
        choices=["DNS_TXT", "DNS_CNAME", "FILE", "META", "ANALYTICS", "TAG_MANAGER"],
        default="DNS_TXT",
    )
    verify_parser.set_defaults(func=verify_site)

    add_parser = subparsers.add_parser("add-property", help="Add a Search Console property")
    add_common_auth_args(add_parser)
    add_parser.add_argument("property", help="Search Console property, such as sc-domain:example.com")
    add_parser.set_defaults(func=add_property)

    sitemap_parser = subparsers.add_parser("submit-sitemap", help="Submit a sitemap to Search Console")
    add_common_auth_args(sitemap_parser)
    sitemap_parser.add_argument("property", help="Search Console property")
    sitemap_parser.add_argument("sitemap", help="Absolute sitemap URL")
    sitemap_parser.set_defaults(func=submit_sitemap)

    inspect_parser = subparsers.add_parser("inspect-url", help="Inspect indexed URL status")
    add_common_auth_args(inspect_parser)
    inspect_parser.add_argument("property", help="Search Console property")
    inspect_parser.add_argument("url", help="Fully qualified URL under the property")
    inspect_parser.add_argument("--language-code", default="en-US")
    inspect_parser.set_defaults(func=inspect_url)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
