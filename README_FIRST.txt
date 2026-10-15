GORESULT HUB — COMPLETE WEBSITE + MONITORING RECOVERY PACKAGE
============================================================

This ZIP includes BOTH the website (site/) and monitoring system (checker/), plus GitHub Actions workflows. It is intended as a full replacement package because previous site files were deleted.

IMPORTANT LIMITS
- The registry has a broad starter set of 162 configured official-source entries. These are NOT 162 independently verified live feeds and do not guarantee literal coverage of every exam/announcement in India.
- The monitor checks public HTTPS HTML/RSS links. It does not universally parse dynamic pages, every PDF, CAPTCHA-protected pages, candidate portals, or APIs. Failed sources are logged and need follow-up.
- Detection is heuristic. A matching link is a candidate, not proof a result is genuine. Keep AUTO_PUBLISH=0 and review Telegram drafts/logs.
- Do not disable TLS verification. Do not collect candidates' passwords, OTPs, registration data, or CAPTCHA answers. Candidate-specific results should link to the authority's official portal.
- Support/donation checkout is a placeholder; no payment processor is configured. AdSense is not configured or guaranteed approved. Verify privacy, contact, domain and content policies before applying.
- GitHub Pages deployment requires Pages to be configured to deploy with GitHub Actions in repository Settings > Pages. A custom domain requires DNS setup separately.

PACKAGE STRUCTURE
- site/ : responsive blue/white portal, search/filter, result cards, policy pages, data/results.json
- checker/check.py : concurrent official-source checker; TLS verification stays on
- checker/sources.json : broad national/state source registry
- checker/state.json : checker history
- .github/workflows/check-results.yml : scheduled/manual checker
- .github/workflows/deploy-pages.yml : website deployment
- requirements.txt : Python dependencies

RESTORE / UPLOAD STEPS
1. Download this ZIP and extract it.
2. Open your GitHub repository: https://github.com/Pooja0330/Resulthub_website
3. If you deleted files, this package restores the intended structure. In GitHub's repository root, upload the CONTENTS of the extracted GoResultHub_Complete_Recovery folder, including the hidden .github folder. Do not upload the ZIP itself. If GitHub web upload makes .github difficult, use GitHub Desktop or git to commit the extracted files.
4. Commit to the main branch.
5. In repository Settings > Pages, choose GitHub Actions as the build/deployment source.
6. In repository Settings > Secrets and variables > Actions, preserve/add secrets TG_TOKEN, TG_ADMIN (numeric Telegram user ID), TG_CHANNEL (for example @resulhub_alerts if that is your actual channel). Never put bot tokens in files.
7. Add repository variable AUTO_PUBLISH with value 0. Do not set it to 1 yet.
8. Actions > deploy-pages workflow: confirm it completes. Then Actions > GoResultHub Official Source Monitor: run once in review mode.
9. Check the logs and Telegram drafts. Fix failed source URLs before treating the system as comprehensive.

IF YOU ALREADY DELETED THE REPOSITORY FILES
Upload every file/folder in this package to the repository root and commit. The package includes the site folder; it is not just a checker patch. GitHub Pages must be configured as above.

TEST STATUS
Local Python syntax and JSON parsing should be checked before upload; no claim is made that every external source was live-tested. Website visual behavior, domain DNS, Telegram credentials, custom-domain routing, payments, and AdSense must be validated in your own GitHub/domain setup.
