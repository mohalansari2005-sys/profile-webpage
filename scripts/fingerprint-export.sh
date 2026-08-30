#!/usr/bin/env bash
# Fingerprint a Next.js static export, ignoring the per-build random buildId.
# Two builds of identical source MUST produce the same fingerprint.
# Usage: scripts/fingerprint-export.sh <out-dir>
# Before running, rm -rf the export directory and rebuild — the script
# fingerprints whatever it finds in <out-dir>, so a stale/contaminated
# export will be fingerprinted as-is and the result won't reflect a clean build.
set -euo pipefail
export LC_ALL=C
d="${1%/}"
candidates=$(ls "$d/_next/static" | grep -Ev '^(chunks|media|css)$')
count=$(printf '%s\n' "$candidates" | grep -c . || true)
if [ "$count" -ne 1 ]; then
  echo "fingerprint-export: expected exactly one build-ID entry under $d/_next/static (excluding chunks/media/css), found $count: $(printf '%s ' $candidates)" >&2
  exit 1
fi
id="$candidates"
find "$d" -type f | while read -r f; do
  rel="${f#"$d"/}"
  if grep -Iq . "$f" 2>/dev/null; then
    h=$(sed "s|$id|__BUILDID__|g" "$f" | shasum | awk '{print $1}')   # text
  else
    h=$(shasum "$f" | awk '{print $1}')                                # binary
  fi
  echo "$h ${rel//$id/__BUILDID__}"
done | sort | shasum | awk '{print $1}'
