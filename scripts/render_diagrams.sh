#!/usr/bin/env bash
# docs/diagrams/*.mmd を docs/images/*.svg にレンダリングする。
# 図を直したら .mmd を編集してこのスクリプトを実行し、SVGごとコミットする。
# 要 node(npx)。初回は mermaid-cli が headless Chromium をダウンロードする。
set -eu

cd "$(dirname "$0")/.."

for mmd in docs/diagrams/*.mmd; do
  svg="docs/images/$(basename "${mmd%.mmd}").svg"
  npx -y @mermaid-js/mermaid-cli@11 -i "$mmd" -o "$svg" -b white
  echo "rendered: $svg"
done
