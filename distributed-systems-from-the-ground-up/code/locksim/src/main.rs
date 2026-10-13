//! Command locksim shows why a lock that expires needs a fencing token. A
//! client that holds the lock pauses for longer than the lock lasts. A
//! second client takes the lock and writes. The first client then wakes up
//! and writes too. The storage accepts only the write with the newer token.
//!
//! Run it from code/ with:
//!
//!     cargo run -p locksim

// ANCHOR: lock
/// A lock that is held for a limited time, called a lease.
struct LockService {
    /// The holder and the time at which its lease ends.
    holder: Option<(String, u64)>,
    /// The token given with the last lease. Every lease gets a higher one.
    token: u64,
}

impl LockService {
    /// Gives the lock to `client` for 10 seconds if it is free or its lease
    /// has ended, and returns the fencing token of the new lease.
    fn acquire(&mut self, client: &str, now: u64) -> Option<u64> {
        if let Some((holder, until)) = &self.holder
            && now < *until
            && holder != client
        {
            return None;
        }

        self.token += 1;
        self.holder = Some((client.to_owned(), now + 10));

        Some(self.token)
    }
}
// ANCHOR_END: lock

// ANCHOR: storage
/// The resource that the lock protects. It remembers the highest token it
/// has seen and refuses a write that carries a lower one.
struct Storage {
    value: String,
    highest: u64,
}

impl Storage {
    fn write(&mut self, token: u64, value: &str) -> bool {
        if token < self.highest {
            return false;
        }

        self.highest = token;
        self.value = value.to_owned();

        true
    }
}
// ANCHOR_END: storage

// ANCHOR: main
fn main() {
    let mut locks = LockService {
        holder: None,
        token: 0,
    };
    let mut storage = Storage {
        value: String::new(),
        highest: 0,
    };

    let first = locks.acquire("client-a", 0);
    println!("t=0   client-a acquires the lock: token {first:?}, lease until t=10");

    println!(
        "t=1   client-b asks for the lock: {:?}",
        locks.acquire("client-b", 1)
    );
    println!("t=2   client-a stops for 15 seconds (a long pause of its process)");

    let second = locks.acquire("client-b", 12);
    println!("t=12  the lease has ended. client-b acquires the lock: token {second:?}");

    if let Some(token) = second {
        let accepted = storage.write(token, "written by client-b");
        println!("t=13  client-b writes with token {token}: accepted {accepted}");
    }

    if let Some(token) = first {
        let accepted = storage.write(token, "written by client-a");
        println!(
            "t=17  client-a wakes up, still believes it holds the lock, writes with token {token}: accepted {accepted}"
        );
    }

    println!("the storage holds: {}", storage.value);
}
// ANCHOR_END: main
