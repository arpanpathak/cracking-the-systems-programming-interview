// ch06/cas_ordering.rs: compare_exchange_weak CAS loop, Acquire-Release
// message passing, and a lock-free Seqlock snapshot reader/writer.
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering, compiler_fence, fence};
use std::thread;

fn update_max(max_val: &AtomicU64, candidate: u64) {
    let mut prev = max_val.load(Ordering::Relaxed);
    while candidate > prev {
        match max_val.compare_exchange_weak(
            prev,
            candidate,
            Ordering::Release,
            Ordering::Relaxed,
        ) {
            Ok(_) => break,
            Err(actual) => prev = actual,
        }
    }
}

struct Seqlock {
    seq: AtomicU64,
    slot_ticks: AtomicU64,
    slot_ns: AtomicU64,
}

impl Seqlock {
    const fn new() -> Self {
        Self {
            seq: AtomicU64::new(0),
            slot_ticks: AtomicU64::new(0),
            slot_ns: AtomicU64::new(0),
        }
    }

    fn write(&self, ticks: u64, scaled_ns: u64) {
        let s = self.seq.load(Ordering::Relaxed);
        self.seq.store(s + 1, Ordering::Release);
        compiler_fence(Ordering::AcqRel);
        self.slot_ticks.store(ticks, Ordering::Relaxed);
        self.slot_ns.store(scaled_ns, Ordering::Relaxed);
        self.seq.store(s + 2, Ordering::Release);
    }

    fn read(&self) -> (u64, u64) {
        loop {
            let s1 = self.seq.load(Ordering::Acquire);
            if (s1 & 1) != 0 {
                continue;
            }
            let t = self.slot_ticks.load(Ordering::Relaxed);
            let ns = self.slot_ns.load(Ordering::Relaxed);
            fence(Ordering::Acquire);
            let s2 = self.seq.load(Ordering::Relaxed);
            if s1 == s2 {
                return (t, ns);
            }
        }
    }
}

fn main() {
    let peak = AtomicU64::new(0);
    thread::scope(|s| {
        for id in 1..=4_u64 {
            let peak_ref = &peak;
            s.spawn(move || {
                for step in 1..=25_000_u64 {
                    update_max(peak_ref, id * step);
                }
            });
        }
    });

    let payload = AtomicU64::new(0);
    let ready = AtomicBool::new(false);
    let mut observed_payload = 0_u64;

    thread::scope(|s| {
        s.spawn(|| {
            payload.store(0xCAFE_BABE_2026, Ordering::Relaxed);
            ready.store(true, Ordering::Release);
        });
        s.spawn(|| {
            while !ready.load(Ordering::Acquire) {}
            observed_payload = payload.load(Ordering::Relaxed);
        });
    });

    let clock_lock = Seqlock::new();
    let done = AtomicBool::new(false);
    let mut torn_reads = 0_u64;

    thread::scope(|s| {
        s.spawn(|| {
            for i in 1..=50_000_u64 {
                clock_lock.write(i, i * 10);
            }
            done.store(true, Ordering::Release);
        });
        s.spawn(|| {
            while !done.load(Ordering::Acquire) {
                let (ticks, scaled_ns) = clock_lock.read();
                if scaled_ns != ticks * 10 {
                    torn_reads += 1;
                }
            }
        });
    });

    println!("cas peak value   : {}", peak.load(Ordering::Relaxed));
    println!("acq-rel payload  : 0x{observed_payload:x}");
    println!("seqlock torn     : {torn_reads}");
}
