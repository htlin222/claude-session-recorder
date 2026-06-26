#!/usr/bin/env bash
# ssh lesson environment — everything lives ONLY inside this clip's intermediate/,
# never the real ~/.ssh. We do NOT pre-create the key pair: scene 3 generates it
# live with `ssh-keygen -t ed25519 ... -f ./id_demo -N ''`, and a pre-existing
# id_demo would make ssh-keygen prompt "Overwrite (y/n)?" — interactive, which
# would break the render. So we delete any leftover key material instead, and
# only lay down the two SAMPLE files the later scenes read: a ~/.ssh-style
# `config` (Host blocks) and a `known_hosts` for the destructive -R demo.
# Idempotent.
set -euo pipefail
DEMO="$(cd "$(dirname "$0")" && pwd)/intermediate"
mkdir -p "$DEMO"
cd "$DEMO"

# scene 3 creates these live; wipe leftovers so ssh-keygen never prompts.
rm -f id_demo id_demo.pub
# scene 12 (ssh-keygen -R) rewrites known_hosts and drops a .old backup; clear it.
rm -f config known_hosts known_hosts.old

# a sample ~/.ssh/config: a named Host block (web) plus a catch-all.
cat > config <<'EOF'
Host web
    HostName web.example.com
    User deploy
    Port 2222
    IdentityFile ~/.ssh/id_demo

Host *
    ServerAliveInterval 60
EOF

# a sample known_hosts with two entries; scene 12 removes the `oldserver` one.
cat > known_hosts <<'EOF'
oldserver ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFaHLEIes7KmIqnsjVwLBgjjBYmwlaQY4kiXe1IHAVCw
web.example.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBQ2RTb0n8sxhY4nGZ0n8sxhY4nGZ0n8sxhY4nGZ0n
EOF

echo "reset done (ssh)."
