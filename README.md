# Google Search Console Skill

Codex skill and helper scripts for listing owned websites in Google Search Console.

The workflow uses Google APIs where they are stable and keeps the manual boundary explicit where Google requires ownership proof:

- Generate Google Site Verification tokens.
- Verify DNS, file, or meta token placement.
- Add Search Console properties.
- Submit sitemaps.
- Inspect indexed URL status.

Google Cloud Console is used only to enable APIs and create OAuth credentials. The Search Console account context is `milotheassistant@gmail.com` under organization `502896413119`.

Start with:

```powershell
python scripts/gsc_workflow.py preflight https://example.com
python -m pip install -r scripts/requirements.txt
python scripts/gsc_workflow.py --help
```

See `SKILL.md` and `references/` for the full Codex workflow.
