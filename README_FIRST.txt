GoResultHub Full Release - deployable starter project

PLEASE READ:
This is a deployable, self-contained release candidate, not a guarantee that every Indian exam announcement is detected. No honest package can promise complete nationwide coverage without validating each authority's live source and adding adapters for changing portals, PDFs, APIs and login-protected systems.

It includes:
- Static responsive website with search, category/state filters, source links and supporter button placeholder
- JSON data store for announcements
- Scheduled GitHub Actions checker for official HTML/RSS sources
- Deduplication, source failure logs, Telegram admin/channel messages
- Review-first publication; safe publishing toggle
- Source registry seed for major national agencies and a starter set of state/board sources
- Basic policy pages and disclaimer
- Cloudflare/hosting and payment integration notes

Deployment:
1. Download and extract the ZIP.
2. Back up your existing repository first (GitHub -> Code -> Download ZIP).
3. Replace the repository contents with this package only if you are willing to replace the old site. Existing GitHub repository secrets/variables normally remain in GitHub settings, but verify them.
4. Keep the repository's default branch as main.
5. Set repository Actions variable AUTO_PUBLISH to 0.
6. Ensure repository secrets TG_TOKEN, TG_ADMIN and TG_CHANNEL exist. Never put bot tokens in source files.
7. In Actions, manually run "GoResultHub Official Source Monitor" in review mode. Inspect logs and Telegram messages.
8. Verify the homepage deployment workflow runs successfully and check your live site.
9. Only enable AUTO_PUBLISH=1 after several days of reviewed detections and only if you accept the risk of false positives.

Important:
- GitHub Pages is static hosting; GitHub Actions writes site/data/results.json and commits it. GitHub Pages deploy workflow publishes the static site.
- For a result that requires a candidate login, the website links to the authority's own page. It must not clone an official login or collect passwords/OTPs.
- Support payments: button is intentionally a placeholder until you choose and configure a hosted payment provider. Never expose payment secret keys in browser code.
- Domain/CDN: connect Cloudflare after confirming DNS records and the current live site.
- No universal scraper can bypass CAPTCHAs, private candidate portals or access restrictions. Respect source terms and rate limits.
