#!/bin/sh
# Runs every model program in Go and in Rust and compares what each prints
# with the output the chapters include from code/output/. A difference means
# a chapter shows output that the code no longer produces.
#
#   tools/check_outputs.sh
set -u
root=$(cd "$(dirname "$0")/.." && pwd)
status=0
for name in fleethealth fencing provisioner migration allreduce gangsched counter cas; do
    want="$root/code/output/$name.txt"
    if ! (cd "$root/code/go" && go run "./$name") 2>&1 | cmp -s - "$want"; then
        echo "go   $name: output differs from code/output/$name.txt"
        status=1
    fi
    if ! (cd "$root/code/rust" && cargo run -q -p "$name") 2>&1 | cmp -s - "$want"; then
        echo "rust $name: output differs from code/output/$name.txt"
        status=1
    fi
done
[ "$status" -eq 0 ] && echo "every program prints the output its chapter shows"
exit "$status"
