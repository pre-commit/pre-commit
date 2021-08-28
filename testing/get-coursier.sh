#!/usr/bin/env bash
# This is a script used in CI to install coursier
set -euo pipefail

COURSIER_URL="https://github.com/coursier/coursier/releases/download/v2.0.0/cs-x86_64-pc-linux"
COURSIER_HASH="e2e838b75bc71b16bcb77ce951ad65660c89bda7957c79a0628ec7146d35122f"
ARTIFACT="/tmp/coursier/cs"

mkdir -p /tmp/coursier
rm -f "$ARTIFACT"
curl --location --silent --output "$ARTIFACT" "$COURSIER_URL"
echo "$COURSIER_HASH  $ARTIFACT" | sha256sum --check
chmod ugo+x /tmp/coursier/cs

echo '##vso[task.prependpath]/tmp/coursier'
