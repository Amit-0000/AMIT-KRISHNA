#!/bin/sh
# Runs as root (the image's default USER, see api/Dockerfile /
# api/Dockerfile.ml) so it can fix up ownership on docker-compose's
# ./data/uploads bind mount before handing off to the real, unprivileged
# process -- a bind-mounted host directory keeps whatever UID created it
# (root, if Docker auto-created it because it didn't exist yet, which is
# exactly what happens on a fresh CI checkout or a fresh host clone), and
# the image's own build-time `chown -R appuser:appuser /app` only ever
# touches the image's baked-in filesystem, never a bind mount layered over
# it at *run* time. Confirmed live (not assumed): api/main.py's feature-
# extraction write to /app/data/uploads/features/*.npy failed with a real
# `PermissionError: [Errno 13]` under appuser (uid 1000) against a
# root-owned bind-mounted uploads directory -- the previous version of this
# security-review.md F-25 fix (USER appuser as the image's last
# instruction, no entrypoint) claimed Docker Desktop "handles this
# transparently"; it does not, at least not for a directory Docker itself
# auto-creates on first `docker compose up`.
set -e

mkdir -p /app/data/uploads
chown -R appuser:appuser /app/data/uploads

exec su appuser -s /bin/sh -c "$*"
