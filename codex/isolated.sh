#!/bin/bash
# Run a command in an isolated filesystem view for a PUK experiment.
# Visible under /home2: only the experiment folder (read-write) and the tool
# installations listed in RO_PATHS (read-only). Everything else under HIDE_ROOT
# and /tmp is an empty tmpfs, so earlier results cannot be read.
# Usage: RO_PATHS="/path/to/conda /path/to/lmp ..." HIDE_ROOT=/home2 isolated.sh <experiment dir> <command...>
set -eu
DIR=$(realpath "$1"); shift
HIDE_ROOT=${HIDE_ROOT:-/home}
args=(--ro-bind / / --tmpfs "$HIDE_ROOT" --tmpfs /tmp)
for p in ${RO_PATHS:-}; do args+=(--ro-bind "$p" "$p"); done
exec bwrap "${args[@]}" --bind "$DIR" "$DIR" --dev /dev --proc /proc \
  --chdir "$DIR" --setenv HOME "$HOME" --die-with-parent "$@"
