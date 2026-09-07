#!/usr/bin/env bash
#
# Tear down every process left over from a simulation run, then clear the
# FastDDS shared-memory segments.
#
# Why this is a script and not a one-liner in pixi.toml
# ----------------------------------------------------
# Two things have to be right, and both were wrong in the previous inline
# version:
#
#   1. ORDER OF SIGNALS. "ros2 launch" is the parent of every node in the
#      system. SIGKILL it and it never runs its own shutdown, so all of its
#      children are orphaned and reparented to init -- still running, still
#      registered in the ROS graph, still publishing. A stale /clock bridge
#      from a previous world is enough to make the next run hang forever on
#      "No clock received", because a fresh subscriber can match the dead
#      publisher and then wait for messages that will never come. So: SIGTERM
#      launch first, give it time to reap its children, and only escalate to
#      SIGKILL for whatever is genuinely stuck.
#
#   2. ORDER OF CLEANUP. Removing /dev/shm/fastrtps_* while a process still
#      has those files open does NOT free them. The unlinked inode stays
#      locked by the surviving process, the next run creates a new file with
#      the same name, and FastDDS fails to lock it:
#          [RTPS_TRANSPORT_SHM Error] Failed init_port fastrtps_port7024:
#          open_and_lock_file failed
#      which surfaces as service calls timing out all over the launch. So the
#      shm sweep happens LAST, and only once nothing is left alive.
#
# Matching is done on absolute workspace paths rather than bare process names.
# Every simulation node runs out of either the pixi env's lib/ directory or the
# colcon install/ tree, so the paths are both complete and specific -- and
# because they live in this file rather than in a shell -c string, no pattern
# can match the cleanup process's own command line (the bug that made earlier
# versions kill themselves).

#
# Pass --dry-run to list what would be killed without signalling anything.

set -uo pipefail

DRY_RUN=0
[[ ${1:-} == --dry-run ]] && DRY_RUN=1

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Anything whose command line matches one of these belongs to a sim run.
PATTERNS=(
    "${WS}/.pixi/envs/default/lib/"   # ros_gz_bridge, nav2, rviz2, spawners, ...
    "${WS}/install/"                  # mission_node, relocate_robot, ...
    "gz-sim-server"
    "gz-sim-gui"
    "gz sim"
)

# Never signal ourselves or any of our ancestors.
protected() {
    local pid=$1 self=$$
    while [[ $pid -gt 1 ]]; do
        [[ $pid -eq $self ]] && return 0
        pid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
        [[ -z $pid ]] && break
    done
    return 1
}

survivors() {
    local pat pid out=()
    for pat in "${PATTERNS[@]}"; do
        while read -r pid; do
            [[ -z $pid ]] && continue
            protected "$pid" && continue
            out+=("$pid")
        done < <(pgrep -f -- "$pat" 2>/dev/null)
    done
    printf '%s\n' "${out[@]+"${out[@]}"}" | sort -un
}

signal_all() {
    local sig=$1 pid n=0
    while read -r pid; do
        [[ -z $pid ]] && continue
        kill "-${sig}" "$pid" 2>/dev/null && n=$((n + 1))
    done < <(survivors)
    echo "$n"
}

wait_clear() {
    local deadline=$((SECONDS + $1))
    while [[ $SECONDS -lt $deadline ]]; do
        [[ -z "$(survivors)" ]] && return 0
        sleep 0.5
    done
    return 1
}

if [[ $DRY_RUN -eq 1 ]]; then
    found="$(survivors)"
    if [[ -z $found ]]; then
        echo "sim-clean: nothing running -- clean"
        exit 0
    fi
    echo "sim-clean: would stop these (PPID 1 means orphaned by an earlier kill):"
    ps -o pid,ppid,etime,cmd -p "$(echo "$found" | tr '\n' ',' | sed 's/,$//')" 2>/dev/null
    exit 0
fi

# ---------------------------------------------------------------- phase 1 ---
# Ask ros2 launch to shut down. It signals each of its own nodes in turn, which
# is the only path that leaves nothing orphaned.
launch_pids=$(pgrep -f -- 'ros2 launch' 2>/dev/null | while read -r p; do
    protected "$p" || echo "$p"
done)
if [[ -n $launch_pids ]]; then
    echo "sim-clean: asking ros2 launch to shut down ($(echo "$launch_pids" | wc -l) found)"
    # shellcheck disable=SC2086
    kill -TERM $launch_pids 2>/dev/null
    wait_clear 12 && { echo "sim-clean: launch shut down cleanly"; }
fi

# ---------------------------------------------------------------- phase 2 ---
# Whatever launch did not own, or did not manage to stop: orphans from earlier
# kills, nodes started by hand, a detached gazebo.
if [[ -n "$(survivors)" ]]; then
    n=$(signal_all TERM)
    [[ $n -gt 0 ]] && echo "sim-clean: SIGTERM to $n leftover process(es)"
    wait_clear 8
fi

# ---------------------------------------------------------------- phase 3 ---
if [[ -n "$(survivors)" ]]; then
    n=$(signal_all KILL)
    [[ $n -gt 0 ]] && echo "sim-clean: SIGKILL to $n stuck process(es)"
    wait_clear 5
fi

# ---------------------------------------------------------------- phase 4 ---
# Only now is it safe to drop the shared-memory segments.
remaining="$(survivors)"
if [[ -n $remaining ]]; then
    echo "sim-clean: WARNING -- these refused to die, leaving /dev/shm alone:"
    ps -o pid,etime,cmd -p "$(echo "$remaining" | tr '\n' ',' | sed 's/,$//')" 2>/dev/null | tail -n +2
    echo "sim-clean: removing shm files now would break the next run; kill them by hand first"
    exit 1
fi

shm=$(ls /dev/shm 2>/dev/null | grep -c '^\(sem\.\)\?fastrtps' || true)
rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_* 2>/dev/null
echo "sim-clean: cleared ${shm} FastDDS shm segment(s)"
echo "sim-clean: clean"
