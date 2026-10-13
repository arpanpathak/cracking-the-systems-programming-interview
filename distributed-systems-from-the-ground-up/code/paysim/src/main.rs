//! Command paysim moves money between accounts in a ledger. A transfer
//! that is sent twice with the same key happens once, a transfer without
//! enough money is refused, and the total of all accounts stays the same.
//!
//! Run it from code/ with:
//!
//!     cargo run -p paysim

// ANCHOR: imports
use std::collections::BTreeMap;
// ANCHOR_END: imports

// ANCHOR: ledger
/// The result of asking for a transfer.
#[derive(Clone, Copy, Debug, PartialEq)]
enum Outcome {
    Done,
    Refused,
}

/// A ledger: the balance of each account in cents, and the outcome of
/// every transfer by its key.
struct Ledger {
    balances: BTreeMap<String, i64>,
    transfers: BTreeMap<String, Outcome>,
}

impl Ledger {
    /// Moves `cents` from one account to another. A key that was used
    /// before returns the earlier outcome and moves nothing.
    fn transfer(&mut self, key: &str, from: &str, to: &str, cents: i64) -> Outcome {
        if let Some(&earlier) = self.transfers.get(key) {
            return earlier;
        }

        let outcome = self.settle(from, to, cents);

        self.transfers
            .insert(key.to_owned(), outcome);

        outcome
    }

    /// Writes the 2 entries of a transfer, if `from` holds enough: what
    /// leaves one account enters the other.
    fn settle(&mut self, from: &str, to: &str, cents: i64) -> Outcome {
        let available = self
            .balances
            .get(from)
            .copied()
            .unwrap_or_default();

        if available < cents {
            return Outcome::Refused;
        }

        *self
            .balances
            .entry(from.to_owned())
            .or_default() -= cents;
        *self
            .balances
            .entry(to.to_owned())
            .or_default() += cents;

        Outcome::Done
    }

    fn total(&self) -> i64 {
        self.balances.values().sum()
    }
}
// ANCHOR_END: ledger

// ANCHOR: main
fn main() {
    let mut ledger = Ledger {
        balances: BTreeMap::from([("ada".to_owned(), 10_000), ("shop".to_owned(), 0)]),
        transfers: BTreeMap::new(),
    };

    println!("start: {:?}, total {}", ledger.balances, ledger.total());

    let requests = [
        ("order-7", "ada", "shop", 4_000),
        ("order-7", "ada", "shop", 4_000),
        ("order-8", "ada", "shop", 9_000),
        ("order-9", "ada", "shop", 6_000),
        ("order-9", "ada", "shop", 6_000),
    ];

    for (key, from, to, cents) in requests {
        let outcome = ledger.transfer(key, from, to, cents);

        println!(
            "{key}: {cents} cents from {from} to {to}: {outcome:?}, ada has {}",
            ledger.balances["ada"]
        );
    }

    println!("end: {:?}, total {}", ledger.balances, ledger.total());
}
// ANCHOR_END: main
