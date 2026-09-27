#!/usr/bin/env bash
# Makes the Jetson's integrated GPU usable from pods in a kind cluster.
#
# A kind node is a privileged container, so it already sees the GPU's device
# files. It lacks three things that the host has: the driver libraries listed
# in the Tegra CSV files, the NVIDIA Container Toolkit binaries, and a
# containerd configuration that uses nvidia-container-runtime. This script
# copies the first two into every node and then uses nvidia-ctk, inside the
# node, to configure the runtime as NVIDIA's documentation describes.
#
# Usage: ./enable-gpu-in-kind.sh [cluster-name]
set -euo pipefail

cluster="${1:-gpu-lab}"
csv_dir=/etc/nvidia-container-runtime/host-files-for-container.d
toolkit=(/usr/bin/nvidia-container-runtime /usr/bin/nvidia-container-runtime-hook
         /usr/bin/nvidia-ctk /usr/bin/nvidia-cdi-hook
         /etc/nvidia-container-runtime/config.toml)

# Every file named in the CSV lists that exists on this board. Device nodes
# are left out, because the privileged node already has them.
mapfile -t host_files < <(cut -d, -f2 "$csv_dir"/*.csv | tr -d ' ' | sort -u |
    grep -v '^/dev/' | while read -r f; do [[ -e $f ]] && echo "$f"; done)

for node in $(kind get nodes --name "$cluster"); do
    echo "$node: copying ${#host_files[@]} driver files and the container toolkit"
    # The runtime bind-mounts the CSV "lib" entries and recreates the "sym"
    # entries as links, so symlinks must arrive as symlinks. Paths that are
    # links on the host are removed first, in case an earlier copy left a
    # regular file or directory there.
    for f in "${host_files[@]}"; do [[ -L $f ]] && echo "$f"; done |
        docker exec -i "$node" xargs rm -rf
    tar -cf - --hard-dereference "${host_files[@]}" "$csv_dir" "${toolkit[@]}" 2>/dev/null |
        docker exec -i "$node" tar -xf - -C /

    # The host runs Ubuntu, where the real ldconfig is /sbin/ldconfig.real.
    # The kind node runs Debian, where it is /sbin/ldconfig.
    docker exec "$node" nvidia-ctk config --in-place \
        --set nvidia-container-cli.ldconfig=@/sbin/ldconfig

    if docker exec "$node" grep -q 'default_runtime_name = "nvidia"' /etc/containerd/config.toml; then
        echo "$node: containerd already uses the nvidia runtime by default"
        continue
    fi
    echo "$node: configuring containerd and restarting it"
    docker exec "$node" nvidia-ctk runtime configure --runtime=containerd --set-as-default
    docker exec "$node" systemctl restart containerd
done
