//! Command bookingsim sells the seats of a small cinema. 2 buyers want the
//! same seat. A seat is first held for a few minutes and then paid for, and
//! a hold that is not paid in time lets the seat go.
//!
//! Run it from code/ with:
//!
//!     cargo run -p bookingsim

// ANCHOR: seats
#[derive(Clone, Debug, PartialEq)]
enum Seat {
    Free,
    /// Held for a buyer until a time. Nobody else can take it before then.
    Held {
        buyer: String,
        until: u64,
    },
    Sold {
        buyer: String,
    },
}

struct Cinema {
    seats: Vec<Seat>,
}

impl Cinema {
    /// Holds a seat for 5 minutes, if it is free or its hold has run out.
    fn hold(&mut self, seat: usize, buyer: &str, now: u64) -> bool {
        let available = match &self.seats[seat] {
            Seat::Free => true,
            Seat::Held { until, .. } => now >= *until,
            Seat::Sold { .. } => false,
        };

        if available {
            self.seats[seat] = Seat::Held {
                buyer: buyer.to_owned(),
                until: now + 5,
            };
        }

        available
    }

    /// Sells a seat to the buyer who holds it, if the hold is still valid.
    fn pay(&mut self, seat: usize, buyer: &str, now: u64) -> bool {
        let valid = matches!(&self.seats[seat], Seat::Held { buyer: holder, until } if holder == buyer && now < *until);

        if valid {
            self.seats[seat] = Seat::Sold {
                buyer: buyer.to_owned(),
            };
        }

        valid
    }
}
// ANCHOR_END: seats

// ANCHOR: main
fn main() {
    let mut cinema = Cinema {
        seats: vec![Seat::Free; 3],
    };

    println!("minute 0: ada holds seat 1: {}", cinema.hold(1, "ada", 0));
    println!("minute 1: bob holds seat 1: {}", cinema.hold(1, "bob", 1));
    println!("minute 1: bob holds seat 2: {}", cinema.hold(2, "bob", 1));
    println!("minute 3: bob pays for seat 2: {}", cinema.pay(2, "bob", 3));
    println!(
        "minute 6: ada's hold has run out. bob holds seat 1: {}",
        cinema.hold(1, "bob", 6)
    );
    println!("minute 7: ada pays for seat 1: {}", cinema.pay(1, "ada", 7));
    println!("minute 8: bob pays for seat 1: {}", cinema.pay(1, "bob", 8));

    for (number, seat) in cinema.seats.iter().enumerate() {
        println!("seat {number}: {seat:?}");
    }
}
// ANCHOR_END: main
