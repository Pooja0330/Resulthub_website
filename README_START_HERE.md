# GoResultHub dynamic results patch

Upload each folder to the matching repository folder. Do NOT delete your existing `.github/workflows/pages.yml`, `site/index.html`, `site/data.js`, or styles.

Files to upload:
- `site/script.js` REPLACE existing script.js
- `site/results.json` NEW
- `checker/check.py` NEW
- `checker/sources.json` NEW: starter sources only; confirm each page and link extraction
- `checker/state.json` NEW: baseline memory
- `.github/workflows/check-results.yml` NEW

In Settings > Secrets and variables > Actions add secrets `TG_TOKEN`, `TG_CHANNEL`, optionally `TG_ADMIN`. Add variable `AUTO_PUBLISH=0` initially. Run Actions > check-results > Run workflow (review). First run baselines current links and will not announce them. Later detections go to admin for manual review; they do not appear on site until approved or AUTO_PUBLISH is enabled.

CAUTION: checker is heuristic. Some official pages render via JavaScript, change markup, block requests or link to a separate login domain. The sample allowed_hosts list needs review. It cannot promise coverage of all IBPS PO or RRB result links. When auto mode is enabled, detections are labelled unverified on the website and in Telegram. `site/results.json` is generated; do not treat entries as confirmed results. For production, add a human approval step.

After committing, keep Pages source GitHub Actions; your existing pages.yml workflow deploys when `site/**` changes. GitHub scheduled workflows can be delayed.
