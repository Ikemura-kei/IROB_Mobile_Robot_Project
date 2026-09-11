#!/usr/bin/env bash
#
# Stop everything left over from a simulation run, then clear its FastDDS shared
# memory. Orphans keep the process group of the `ros2 launch` that started them,
# so signalling whole groups reaches them even once the launch is gone; Gazebo
# sits in its own group and is matched by name. Shared memory goes last: dropping
# it while something still holds it open breaks the next run instead of fixing it.
#
# Pass --dry-run to list what would be stopped without signalling anything.

set -uo pipefail

DRY_RUN=0
[[ ${1:-} == --dry-run ]] && DRY_RUN=1

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SELF_PGID=$(ps -o pgid= -p $$ | tr -d ' ')
ME=$(id -u)

# Anything that unambiguously belongs to a sim run. The pixi environment is in
# the list because an orphan whose launch is already gone matches nothing else.
# Every lookup below is restricted to processes and files you own.
SEEDS=("gz sim" "gz-sim-server" "gz-sim-gui"
       "ros2 launch warehouse_inventory_robot" "${WS}/install/")
[[ -n ${CONDA_PREFIX:-} ]] && SEEDS+=("${CONDA_PREFIX}/lib/")
SEEDS+=("${WS}/pixi/.pixi/envs/default/lib/")

# Process groups containing at least one seed, excluding our own.
groups() {
    local pat pid pgid out=()
    for pat in "${SEEDS[@]}"; do
        while read -r pid; do
            pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
            [[ -z $pgid || $pgid -le 1 || $pgid == "$SELF_PGID" ]] && continue
            out+=("$pgid")
        done < <(pgrep -u "$ME" -f -- "$pat" 2>/dev/null)
    done
    printf '%s\n' "${out[@]+"${out[@]}"}" | sort -un
}

# Every process in those groups -- this is what picks up the orphans.
members() {
    local pgid out=() p
    for pgid in $(groups); do
        while read -r p; do out+=("$p"); done < <(pgrep -g "$pgid" 2>/dev/null)
    done
    printf '%s\n' "${out[@]+"${out[@]}"}" | sort -un
}

signal_groups() {
    local pgid n=0
    for pgid in $(groups); do
        kill "-${1}" "-${pgid}" 2>/dev/null && n=$((n + 1))
    done
    echo "$n"
}

wait_clear() {
    local deadline=$((SECONDS + $1))
    while [[ $SECONDS -lt $deadline ]]; do
        [[ -z "$(members)" ]] && return 0
        sleep 0.5
    done
    return 1
}

show() { ps -o pid,pgid,etime,cmd -p "$(echo "$1" | tr '\n' ',' | sed 's/,$//')" 2>/dev/null; }

found="$(members)"

if [[ $DRY_RUN -eq 1 ]]; then
    [[ -z $found ]] && { echo "sim-clean: nothing running -- clean"; exit 0; }
    echo "sim-clean: would stop these:"
    show "$found"
    exit 0
fi

if [[ -n $found ]]; then
    echo "sim-clean: SIGTERM to $(signal_groups TERM) process group(s)"
    wait_clear 12 || {
        echo "sim-clean: SIGKILL to $(signal_groups KILL) stuck group(s)"
        wait_clear 5
    }
fi

remaining="$(members)"
if [[ -n $remaining ]]; then
    echo "sim-clean: WARNING -- these refused to die, leaving /dev/shm alone:"
    show "$remaining" | tail -n +2
    echo "sim-clean: clearing shm now would break the next run; kill them by hand first"
    exit 1
fi

shmfiles=$(find /dev/shm -maxdepth 1 -user "$ME" \
    \( -name 'fastrtps_*' -o -name 'sem.fastrtps_*' \) 2>/dev/null)
shm=$(printf '%s' "$shmfiles" | grep -c . || true)
[[ -n $shmfiles ]] && printf '%s\n' "$shmfiles" | xargs -r rm -f 2>/dev/null
echo "sim-clean: cleared ${shm} FastDDS shm segment(s) -- clean"
