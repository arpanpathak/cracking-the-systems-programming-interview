#!/usr/bin/env bash
# run_all.sh: compile every listing with strict flags, run it, save the output.
# The .out files this script produces are the exact outputs included in the book.
set -euo pipefail
cd "$(dirname "$0")"

CXX="${CXX:-clang++}"
CXXFLAGS="-std=c++20 -O2 -Wall -Wextra -Werror -pthread"
RUSTFLAGS="-D warnings -O"
EDITION=2024
mkdir -p out

# One cargo build provides the libc rlib used by the Rust listings that
# call raw POSIX interfaces (fork, mmap, sigaction, ...).
(cd libc_bootstrap && cargo build --release --quiet)
LIBC=$(ls libc_bootstrap/target/release/deps/liblibc-*.rlib | head -1)

cxx() {
    $CXX $CXXFLAGS "$1" -o "out/$(basename "$1" .cpp).bin"
}
rs_std() {
    rustc --edition "$EDITION" $RUSTFLAGS "$1" -o "out/$(basename "$1" .rs)_rs.bin"
}
rs_libc() {
    rustc --edition "$EDITION" $RUSTFLAGS --extern libc="$LIBC" "$1" \
        -o "out/$(basename "$1" .rs)_rs.bin"
}
run() {   # run <binary> <output-stem>
    "./$1" > "out/$2.out" 2>&1 || {
        echo "NOTE: $2 exited with status $?" >> "out/$2.out"
    }
}

echo "== compiling =="

# C++ listings
for f in \
    ch03/layout ch03/fork \
    ch04/threads ch04/race ch04/race_atomic \
    ch05/sched_sim \
    ch06/mutex_counter ch06/prodcons ch06/deadlock ch06/trylock ch06/cas_ordering \
    ch07/pagesize ch07/mmap_file ch07/tlb \
    ch08/index_arena ch08/gen_arena ch08/bump ch08/free_list \
    ch09/syscall_cost ch09/write_buffered \
    ch10/signals ch10/sigchld \
    ch11/pipe ch11/shm_counter ch11/socketpair \
    ch12/files ch12/sparse \
    ch13/poll_echo_server ch13/echo_client \
    ch14/udp ch14/getaddrinfo \
    ch15/daemon ch15/kqueue_supervisor \
    ch17/false_sharing \
    ch18/cache_bench \
    ch19/bounded_queue ch19/ring_buffer ch19/ring_buffer_uninit ch19/free_list_allocator ch19/spsc_ring ch19/byte_routines ch19/lru_cache ch19/bit_tricks \
    ch19/linked_list ch19/rw_lock ch19/thread_pool ch19/mini_pipeline; do
    cxx "$f.cpp"
done

# Rust listings that need libc
for f in \
    ch03/fork \
    ch07/pagesize ch07/mmap_file ch07/tlb \
    ch08/bump ch08/free_list \
    ch09/syscall_cost ch09/write_buffered \
    ch10/signals ch10/sigchld \
    ch11/pipe ch11/shm_counter ch11/socketpair \
    ch13/poll_echo_server \
    ch15/daemon ch15/kqueue_supervisor \
    ch19/mini_pipeline; do
    rs_libc "$f.rs"
done

# Rust listings that use only the standard library
for f in \
    ch03/layout \
    ch04/threads ch04/race ch04/race_atomic \
    ch05/sched_sim \
    ch06/mutex_counter ch06/prodcons ch06/deadlock ch06/trylock ch06/cas_ordering \
    ch08/index_arena ch08/gen_arena \
    ch12/files ch12/sparse \
    ch13/thread_echo ch13/echo_client \
    ch14/udp ch14/to_socket_addrs \
    ch17/false_sharing \
    ch18/cache_bench \
    ch19/bounded_queue ch19/ring_buffer ch19/ring_buffer_uninit ch19/free_list_allocator ch19/spsc_ring ch19/byte_routines ch19/lru_cache \
    ch19/bit_tricks ch19/linked_list ch19/rw_lock ch19/thread_pool; do
    rs_std "$f.rs"
done

echo "== running =="

run out/layout.bin ch03_layout
run out/layout_rs.bin ch03_layout_rs
run out/fork.bin ch03_fork
run out/fork_rs.bin ch03_fork_rs

run out/threads.bin ch04_threads
run out/threads_rs.bin ch04_threads_rs
run out/race.bin ch04_race
run out/race_rs.bin ch04_race_rs
run out/race_atomic.bin ch04_race_atomic
run out/race_atomic_rs.bin ch04_race_atomic_rs

run out/sched_sim.bin ch05_sched
run out/sched_sim_rs.bin ch05_sched_rs

run out/mutex_counter.bin ch06_mutex
run out/mutex_counter_rs.bin ch06_mutex_rs
run out/prodcons.bin ch06_prodcons
run out/prodcons_rs.bin ch06_prodcons_rs
run out/trylock.bin ch06_trylock
run out/trylock_rs.bin ch06_trylock_rs
run out/cas_ordering.bin ch06_cas_ordering
run out/cas_ordering_rs.bin ch06_cas_ordering_rs

# deadlock.cpp and deadlock.rs are expected to hang; detect and kill them.
out/deadlock.bin > out/ch06_deadlock.out 2>&1 &
DPID=$!
sleep 1
if kill -0 "$DPID" 2>/dev/null; then
    echo "harness: process still alive after 1 s - deadlocked (killed)" \
        >> out/ch06_deadlock.out
    kill -9 "$DPID"
else
    echo "harness: process exited on its own - no deadlock" >> out/ch06_deadlock.out
fi

out/deadlock_rs.bin > out/ch06_deadlock_rs.out 2>&1 &
DPID=$!
sleep 1
if kill -0 "$DPID" 2>/dev/null; then
    echo "harness: process still alive after 1 s - deadlocked (killed)" \
        >> out/ch06_deadlock_rs.out
    kill -9 "$DPID"
else
    echo "harness: process exited on its own - no deadlock" >> out/ch06_deadlock_rs.out
fi

run out/pagesize.bin ch07_pagesize
run out/pagesize_rs.bin ch07_pagesize_rs
run out/mmap_file.bin ch07_mmap_file
run out/mmap_file_rs.bin ch07_mmap_file_rs
run out/tlb.bin ch07_tlb
run out/tlb_rs.bin ch07_tlb_rs

run out/index_arena.bin ch08_index_arena
run out/index_arena_rs.bin ch08_index_arena_rs
run out/gen_arena.bin ch08_gen_arena
run out/gen_arena_rs.bin ch08_gen_arena_rs
run out/bump.bin ch08_bump
run out/bump_rs.bin ch08_bump_rs
run out/free_list.bin ch08_free_list
run out/free_list_rs.bin ch08_free_list_rs

run out/syscall_cost.bin ch09_syscall_cost
run out/syscall_cost_rs.bin ch09_syscall_cost_rs
run out/write_buffered.bin ch09_write_buffered
run out/write_buffered_rs.bin ch09_write_buffered_rs

run out/signals.bin ch10_signals
run out/signals_rs.bin ch10_signals_rs
run out/sigchld.bin ch10_sigchld
run out/sigchld_rs.bin ch10_sigchld_rs

run out/pipe.bin ch11_pipe
run out/pipe_rs.bin ch11_pipe_rs
run out/shm_counter.bin ch11_shm_counter
run out/shm_counter_rs.bin ch11_shm_counter_rs
run out/socketpair.bin ch11_socketpair
run out/socketpair_rs.bin ch11_socketpair_rs

run out/files.bin ch12_files
run out/files_rs.bin ch12_files_rs
run out/sparse.bin ch12_sparse
run out/sparse_rs.bin ch12_sparse_rs

# Poll-based echo server: start it, run the client twice, wait for the server.
out/poll_echo_server.bin > out/ch13_poll_echo_server.out 2>&1 &
SPID=$!
sleep 0.4
run out/echo_client.bin ch13_echo_client_1
run out/echo_client.bin ch13_echo_client_2
wait "$SPID" || true

out/poll_echo_server_rs.bin > out/ch13_poll_echo_server_rs.out 2>&1 &
SPID=$!
sleep 0.4
run out/echo_client_rs.bin ch13_echo_client_1_rs
run out/echo_client_rs.bin ch13_echo_client_2_rs
wait "$SPID" || true

run out/thread_echo_rs.bin ch13_thread_echo_rs

run out/udp.bin ch14_udp
run out/udp_rs.bin ch14_udp_rs
run out/getaddrinfo.bin ch14_getaddrinfo
run out/to_socket_addrs_rs.bin ch14_to_socket_addrs_rs

# --- daemons ------------------------------------------------------------
daemon_run() {  # daemon_run <binary> <pidfile> <logfile> <outname>
    local bin="$1" pidfile="$2" logfile="$3" name="$4"
    rm -f "$pidfile" "$logfile"
    "./$bin" &
    local launched=$!
    # The first parent exits immediately; the daemon writes the pidfile.
    for _ in $(seq 1 30); do
        [ -f "$pidfile" ] && break
        sleep 0.1
    done
    {
        if [ ! -f "$pidfile" ]; then
            echo "harness: pidfile did not appear"
            return
        fi
        local dpid
        dpid=$(cat "$pidfile")
        echo "harness: daemon running with pid $dpid"
        if kill -0 "$dpid" 2>/dev/null; then
            echo "harness: process alive: yes"
        else
            echo "harness: process alive: NO"
        fi
        kill -HUP "$dpid"
        echo "harness: sent SIGHUP"
        sleep 1.5
        kill -TERM "$dpid"
        echo "harness: sent SIGTERM"
        for _ in $(seq 1 30); do
            [ ! -f "$pidfile" ] && break
            sleep 0.1
        done
        if [ -f "$pidfile" ]; then
            echo "harness: pidfile removed after SIGTERM: NO"
        else
            echo "harness: pidfile removed after SIGTERM: yes"
        fi
        echo "--- daemon log ---"
        cat "$logfile"
    } > "out/$name.out" 2>&1
    wait "$launched" 2>/dev/null || true
}

daemon_run out/daemon.bin /tmp/osbook_daemon.pid /tmp/osbook_daemon.log ch15_daemon
daemon_run out/daemon_rs.bin /tmp/osbook_daemon_rs.pid /tmp/osbook_daemon_rs.log ch15_daemon_rs

run out/kqueue_supervisor.bin ch15_kqueue_supervisor
run out/kqueue_supervisor_rs.bin ch15_kqueue_supervisor_rs

run out/false_sharing.bin ch17_false_sharing
run out/false_sharing_rs.bin ch17_false_sharing_rs

run out/cache_bench.bin ch18_cache_bench
run out/cache_bench_rs.bin ch18_cache_bench_rs

echo "== done: outputs in out/ =="

# Chapter 19: interview problems
for name in bounded_queue ring_buffer ring_buffer_uninit free_list_allocator spsc_ring byte_routines lru_cache bit_tricks linked_list rw_lock thread_pool mini_pipeline; do
    run "out/$name.bin" "ch19_$name"
    run "out/${name}_rs.bin" "ch19_${name}_rs"
done

# Chapter 19: the priority job scheduler (Section 19.13)
for name in quantum_sched priority_workers; do
    cxx "ch19/$name.cpp"
    rs_std "ch19/$name.rs"
    run "out/$name.bin" "ch19_$name"
    run "out/${name}_rs.bin" "ch19_${name}_rs"
done
rs_std ch19/priority_workers_unwrap.rs
run out/priority_workers_unwrap_rs.bin ch19_priority_workers_unwrap_rs
