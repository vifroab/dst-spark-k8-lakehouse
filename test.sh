#!/bin/bash
# test-apt-repos.sh - Test if all Nexus APT repositories are accessible

echo "Testing Nexus APT Repository URLs..."
echo "======================================"

BASE="https://srvnexus1.dst.dk/repository/jammy"

repos=(
  "dists/jammy/main/binary-amd64/Packages.gz"
  "dists/jammy/restricted/binary-amd64/Packages.gz"
  "dists/jammy/universe/binary-amd64/Packages.gz"
  "dists/jammy/multiverse/binary-amd64/Packages.gz"
  "dists/jammy-updates/main/binary-amd64/Packages.gz"
  "dists/jammy-updates/restricted/binary-amd64/Packages.gz"
  "dists/jammy-updates/universe/binary-amd64/Packages.gz"
  "dists/jammy-updates/multiverse/binary-amd64/Packages.gz"
  "dists/jammy-backports/main/binary-amd64/Packages.gz"
  "dists/jammy-backports/universe/binary-amd64/Packages.gz"
  "dists/jammy-security/main/binary-amd64/Packages.gz"
  "dists/jammy-security/restricted/binary-amd64/Packages.gz"
  "dists/jammy-security/universe/binary-amd64/Packages.gz"
  "dists/jammy-security/multiverse/binary-amd64/Packages.gz"
)

echo ""
echo "Testing package indexes:"
for repo in "${repos[@]}"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/$repo")
  if [ "$STATUS" == "200" ]; then
    echo "✓ OK:   $repo"
  else
    echo "✗ FAIL ($STATUS): $repo"
  fi
done

echo ""
echo "Testing InRelease files:"
releases=(
  "dists/jammy/InRelease"
  "dists/jammy-updates/InRelease"
  "dists/jammy-backports/InRelease"
  "dists/jammy-security/InRelease"
)

for rel in "${releases[@]}"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/$rel")
  if [ "$STATUS" == "200" ]; then
    echo "✓ OK:   $rel"
  else
    echo "✗ FAIL ($STATUS): $rel"
  fi
done

echo ""
echo "======================================"
echo "All OK = Repository indexes are accessible"
echo "Note: This only tests indexes, not individual .deb files"

