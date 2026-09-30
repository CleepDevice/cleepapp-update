#!/bin/bash
# CleepOs minor upgrade playbook (same suite, e.g. bullseye → newer bullseye snapshot).
#
# Env:
#   TARGET_CLEEPOS_VERSION  required — value written to /etc/cleepos_version after success
#   CLEEPOS_VERSION_PATH    optional — default /etc/cleepos_version
#
# Exit codes:
#   0 success (caller may reboot)
#   non-zero failure
#
# Phases emit lines: PHASE <name> <begin|end|fail>

set -eu

CLEEPOS_VERSION_PATH="${CLEEPOS_VERSION_PATH:-/etc/cleepos_version}"
LOG_TAG="[cleepos-playbook]"

log() {
  echo "${LOG_TAG} $*"
}

phase_begin() {
  echo
  echo "======== PLAYBOOK PHASE: $1 (begin) ========"
  echo "PHASE $1 begin"
  log "phase $1: begin"
}

phase_end() {
  echo "PHASE $1 end"
  log "phase $1: end"
  echo "======== PLAYBOOK PHASE: $1 (end) ========"
  echo
}

phase_fail() {
  echo "PHASE $1 fail"
  log "phase $1: fail — $2"
  echo "======== PLAYBOOK PHASE: $1 (FAIL) ========"
  exit 1
}

require_target() {
  if [ -z "${TARGET_CLEEPOS_VERSION:-}" ]; then
    phase_fail preflight "TARGET_CLEEPOS_VERSION is not set"
  fi
}

phase_preflight() {
  phase_begin preflight
  require_target
  if [ ! -f "$CLEEPOS_VERSION_PATH" ]; then
    phase_fail preflight "$CLEEPOS_VERSION_PATH missing"
  fi
  current=$(tr -d ' \n' < "$CLEEPOS_VERSION_PATH")
  log "current=${current} target=${TARGET_CLEEPOS_VERSION}"
  if [ "$current" = "$TARGET_CLEEPOS_VERSION" ]; then
    log "already at target version"
    phase_end preflight
    exit 0
  fi
  # same suite only (letters prefix)
  current_suite=$(printf '%s' "$current" | sed 's/[0-9].*//')
  target_suite=$(printf '%s' "$TARGET_CLEEPOS_VERSION" | sed 's/[0-9].*//')
  if [ "$current_suite" != "$target_suite" ]; then
    phase_fail preflight "suite mismatch (${current_suite} -> ${target_suite}); major upgrades need another playbook"
  fi
  phase_end preflight
}

phase_prepare_rw() {
  phase_begin prepare-rw
  if mount | grep -q ' on / .*[(,]ro[,)]'; then
    mount -o remount,rw / || phase_fail prepare-rw "unable to remount / rw"
  fi
  if [ -d /boot ] && mount | grep -q ' on /boot .*[(,]ro[,)]'; then
    mount -o remount,rw /boot || phase_fail prepare-rw "unable to remount /boot rw"
  fi
  phase_end prepare-rw
}

phase_apt() {
  phase_begin apt
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq || phase_fail apt "apt-get update failed"
  # Keep same suite; pull security/point updates.
  apt_log=$(mktemp)
  set -o pipefail
  apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" dist-upgrade \
    2>&1 | tee "$apt_log" \
    || { rm -f "$apt_log"; phase_fail apt "apt-get dist-upgrade failed"; }
  set +o pipefail
  # Parse classic apt summary: "X upgraded, Y newly installed, ..."
  summary=$(grep -E '[0-9]+ upgraded,' "$apt_log" | tail -n1 || true)
  if [ -z "$summary" ]; then
    summary="(no apt summary line — check log above)"
  fi
  log "apt result: $summary"
  mkdir -p /tmp/cleepos-playbook
  printf '%s\n' "$summary" > /tmp/cleepos-playbook/apt-summary.txt
  if echo "$summary" | grep -Eq '^0 upgraded, 0 newly installed, 0 to remove'; then
    log "note: no packages changed — image already current vs apt mirrors; only cleepos_version will be stamped"
  fi
  rm -f "$apt_log"
  apt-get -y autoremove --purge -qq || true
  apt-get -y autoclean -qq || true
  phase_end apt
}

phase_finalize_version() {
  phase_begin finalize-version
  echo "$TARGET_CLEEPOS_VERSION" > "$CLEEPOS_VERSION_PATH" \
    || phase_fail finalize-version "unable to write $CLEEPOS_VERSION_PATH"
  log "wrote $CLEEPOS_VERSION_PATH=$(cat "$CLEEPOS_VERSION_PATH")"
  phase_end finalize-version
}

phase_prepare_ro() {
  phase_begin prepare-ro
  sync || true
  if [ -d /boot ]; then
    mount -o remount,ro /boot || log "warning: could not remount /boot ro"
  fi
  mount -o remount,ro / || log "warning: could not remount / ro (ok if tmpfs writes pending)"
  phase_end prepare-ro
}

phase_preflight
phase_prepare_rw
phase_apt
phase_finalize_version
phase_prepare_ro
log "playbook completed successfully"
exit 0
