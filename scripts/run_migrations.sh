#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/../backend"
alembic upgrade head
