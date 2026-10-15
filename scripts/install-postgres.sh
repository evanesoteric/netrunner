#!/usr/bin/env bash
# Non-root PostgreSQL installation for the Debian 13 cloud development machine.
# APT verifies Debian signatures and package hashes; no trust checks are disabled.
set -euo pipefail
NETRUNNER_TOOLS=/workspace/.netrunner-tools
if [[ -x "$NETRUNNER_TOOLS/postgres/usr/lib/postgresql/17/bin/postgres" ]]; then
  "$NETRUNNER_TOOLS/postgres/usr/lib/postgresql/17/bin/postgres" --version
  exit 0
fi
if ! rg -q '^VERSION_CODENAME=trixie$' /etc/os-release; then
  echo 'Install PostgreSQL 17 for your OS and set NETRUNNER_PG_BIN to its bin directory.' >&2
  exit 1
fi
mkdir -p "$NETRUNNER_TOOLS"/{debs,lists/partial,postgres}
cat > "$NETRUNNER_TOOLS/sources.list" <<'SOURCES'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main
SOURCES
NETRUNNER_APT_OPTIONS=(-o "Dir::Etc::sourcelist=$NETRUNNER_TOOLS/sources.list" -o Dir::Etc::sourceparts=- -o "Dir::State::Lists=$NETRUNNER_TOOLS/lists" -o "APT::Sandbox::User=$(id -un)")
apt-get "${NETRUNNER_APT_OPTIONS[@]}" -o APT::Update::Error-Mode=any update
(cd "$NETRUNNER_TOOLS/debs" && apt-get "${NETRUNNER_APT_OPTIONS[@]}" download postgresql-17 postgresql-client-17)
for package in "$NETRUNNER_TOOLS"/debs/*.deb; do
  dpkg-deb -x "$package" "$NETRUNNER_TOOLS/postgres"
done
"$NETRUNNER_TOOLS/postgres/usr/lib/postgresql/17/bin/postgres" --version
