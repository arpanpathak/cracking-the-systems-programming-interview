//! Command notifysim sends notifications through a provider that sometimes
//! fails. A failed send is tried again after a pause that doubles each
//! time. A notification that still fails after 5 tries is set aside, and a
//! notification that is submitted twice is sent once.
//!
//! Run it from code/ with:
//!
//!     cargo run -p notifysim

// ANCHOR: imports
use std::collections::HashSet;
// ANCHOR_END: imports

// ANCHOR: retry
const TRIES: u32 = 5;

/// The pause before try number `attempt`, in seconds: 1, 2, 4, 8.
fn pause_before(attempt: u32) -> u64 {
    1 << (attempt - 2)
}

/// The outcome of delivering one notification.
enum Outcome {
    Sent { tries: u32, after: u64 },
    SetAside,
}

/// Tries to send until the provider accepts or the tries are used up.
/// `failures` is the number of times the provider fails first.
fn deliver(failures: u32) -> Outcome {
    let Some(tries) = (1..=TRIES).find(|&attempt| attempt > failures) else {
        return Outcome::SetAside;
    };
    let after = (2..=tries).map(pause_before).sum();

    Outcome::Sent { tries, after }
}
// ANCHOR_END: retry

// ANCHOR: main
fn main() {
    // The key of each request, and how often the provider fails for it.
    let requests = [
        ("order-7-shipped", 0),
        ("order-8-shipped", 2),
        ("order-7-shipped", 0),
        ("order-9-shipped", 4),
        ("order-10-shipped", 9),
    ];
    let mut accepted = HashSet::new();

    for (key, failures) in requests {
        if !accepted.insert(key) {
            println!("{key:17} submitted before: not sent again");

            continue;
        }

        match deliver(failures) {
            Outcome::Sent { tries, after } => {
                println!("{key:17} sent on try {tries}, {after} seconds after the first try");
            }
            Outcome::SetAside => {
                println!("{key:17} failed {TRIES} times: set aside for a person to look at");
            }
        }
    }
}
// ANCHOR_END: main
