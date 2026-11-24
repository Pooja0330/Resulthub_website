# Scan from India (fixes the ~170 blocked sources)

Why: GitHub's servers are overseas and many Indian government sites (all RRB railway sites, army/navy/air force,
RPSC, MPPSC, WBPSC, NEET-PG, CISCE ...) time out or refuse them. A small server in India can reach them.
This cannot be guaranteed for every site - some also block automated requests - but it is the only real fix.

## 1. Get a server in India (about 15 minutes)
Any Ubuntu 22.04 or 24.04 server in an Indian region with 1 GB RAM or more is enough, for example:
- Oracle Cloud "Always Free" in Mumbai or Hyderabad (free, but availability varies), or
- AWS Mumbai / DigitalOcean Bangalore / any Indian VPS (roughly Rs 400-800 per month).
Make sure you can log in with SSH.

## 2. Install the runner (5 minutes)
1. GitHub repo -> Settings -> Actions -> Runners -> **New self-hosted runner** -> Linux. Copy only the **token** shown
   in the "Configure" commands (the text after `--token`).
2. On the server run:
   ```
   curl -fsSL https://raw.githubusercontent.com/Pooja0330/Resulthub_website/main/scripts/setup-indian-runner.sh -o setup.sh
   bash setup.sh PASTE_TOKEN_HERE
   ```
3. The runner should show as **Idle** under Settings -> Actions -> Runners.

## 3. Switch scanning to it
Settings -> Secrets and variables -> Actions -> **Variables** -> New repository variable:
`CHECK_RUNNER` = `self-hosted`. Then run Actions -> Check Exam Results -> Run workflow once.
To go back to GitHub's servers at any time, delete that variable.

## 4. Safety (important - public repository)
Settings -> Actions -> General -> "Fork pull request workflows" -> choose **Require approval for all outside
collaborators**. Only the scan job uses your server and it only runs from pushes, the schedule and manual or pinged
triggers; never put personal files or passwords on this server.
