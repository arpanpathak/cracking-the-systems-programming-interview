#!/bin/sh
# Runs every simulation and compares what it prints with the output the
# chapters include from code/output/. A difference means a chapter shows
# output that the code no longer produces.
#
#   tools/check_outputs.sh
set -u
root=$(cd "$(dirname "$0")/.." && pwd)
status=0

for want in "$root"/code/output/*.txt; do
    name=$(basename "$want" .txt)

    if ! (cd "$root/code" && cargo run -q -p "$name") 2>&1 | cmp -s - "$want"; then
        echo "$name: output differs from code/output/$name.txt"
        status=1
    fi
done

[ "$status" -eq 0 ] && echo "every simulation prints the output its chapter shows"
exit "$status"
