#!/usr/bin/env bash
# One-time setup of a GitHub Actions self-hosted runner on an Indian server
# (Ubuntu 22.04/24.04, x86_64 or ARM64). Run as a normal user with sudo:
#   bash setup-indian-runner.sh <REGISTRATION_TOKEN>
# The registration token comes from GitHub: repo Settings > Actions > Runners >
# New self-hosted runner. It expires in about an hour and is used once.
set -euo pipefail

REPO_URL="https://github.com/Pooja0330/Resulthub_website"
TOKEN="${1:-}"
[ -n "$TOKEN" ] || { echo "Usage: bash $0 <REGISTRATION_TOKEN>"; exit 1; }

echo "== Installing packages"
sudo apt-get update -y
sudo apt-get install -y curl git jq python3 python3-venv python3-pip ca-certificates tar
# Node 20 (the workflow syntax-checks the site JavaScript)
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

case "$(uname -m)" in
  x86_64) ARCH=x64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "Unsupported CPU: $(uname -m)"; exit 1 ;;
esac

echo "== Downloading the latest GitHub runner ($ARCH)"
mkdir -p "$HOME/actions-runner" && cd "$HOME/actions-runner"
VERSION="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name | sed 's/^v//')"
curl -fsSL -o runner.tar.gz "https://github.com/actions/runner/releases/download/v${VERSION}/actions-runner-linux-${ARCH}-${VERSION}.tar.gz"
tar xzf runner.tar.gz && rm runner.tar.gz

echo "== Registering the runner"
./config.sh --unattended --url "$REPO_URL" --token "$TOKEN" \
  --name "india-$(hostname)" --labels india --replace

echo "== Installing as a service so it survives reboots"
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status | head -5
echo
echo "Done. Next: in GitHub set repository variable CHECK_RUNNER = self-hosted"
