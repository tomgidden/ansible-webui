#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

last_tag="$(git describe --tags --abbrev=0)"
echo "${last_tag}.dev" > "$(dirname "$0")/../VERSION"
