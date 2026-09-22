#! /bin/bash
#
# Stop a simulation run and everything it left behind, then clear the FastDDS
# shared memory. Ctrl-C on `ros2 launch` does not take Gazebo with it: the launch
# starts a ruby wrapper, and `gz sim server` and `gz sim gui` survive it.
#
# Orphans keep the process group of the launch that started them, so signalling
# whole groups reaches them. Shared memory is cleared last -- dropping it while
# something still holds it open breaks the next run instead of fixing it.

ME=$(id -u)
SELF_PGID=$(ps -o pgid= -p $$ | tr -d ' ')

# PIDs of anything that belongs to a sim run, excluding this script's own group.
sim_pids() {
    ps -u "$ME" -o pid=,pgid=,args= \
      | grep -E 'gz sim|ros2 launch warehouse_inventory_robot|__node:=|parameter_bridge|rviz2' \
      | grep -v ' grep ' \
      | awk -v self="$SELF_PGID" '$2 != self {print $1}'
}

pids=$(sim_pids)
if [ -n "$pids" ]; then
    echo "cleanup: stopping $(echo "$pids" | wc -l) process(es)"
    echo "$pids" | xargs -r kill -INT 2>/dev/null
    for _ in $(seq 1 12); do
        [ -z "$(sim_pids)" ] && break
        sleep 1
    done
    left=$(sim_pids)
    [ -n "$left" ] && echo "$left" | xargs -r kill -9 2>/dev/null
    sleep 2
fi

left=$(sim_pids)
if [ -n "$left" ]; then
    echo "cleanup: WARNING -- these refused to die, leaving /dev/shm alone:"
    ps -o pid,etime,cmd -p "$(echo "$left" | tr '\n' ',' | sed 's/,$//')" 2>/dev/null | tail -n +2
    exit 1
fi

n=$(find /dev/shm -maxdepth 1 -user "$ME" \
      \( -name 'fastrtps_*' -o -name 'sem.fastrtps_*' \) 2>/dev/null | wc -l)
find /dev/shm -maxdepth 1 -user "$ME" \
      \( -name 'fastrtps_*' -o -name 'sem.fastrtps_*' \) -delete 2>/dev/null
ros2 daemon stop >/dev/null 2>&1
echo "cleanup: cleared ${n} FastDDS shm segment(s) -- clean"
