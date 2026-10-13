//! Command matchsim runs the order book of 1 share. It matches each new
//! order against the best prices on the other side, in the order in which
//! the waiting orders arrived, and prints every trade.
//!
//! Run it from code/ with:
//!
//!     cargo run -p matchsim

// ANCHOR: imports
use std::collections::{BTreeMap, VecDeque};
// ANCHOR_END: imports

// ANCHOR: book
#[derive(Clone, Copy, PartialEq)]
enum Side {
    Buy,
    Sell,
}

/// An order to buy or sell a quantity at a price or better. Prices are
/// whole numbers of cents.
#[derive(Clone, Copy)]
struct Order {
    id: u32,
    side: Side,
    price: u32,
    quantity: u32,
}

/// The waiting orders of each side: for every price, a queue in the order
/// of arrival.
#[derive(Default)]
struct Book {
    buys: BTreeMap<u32, VecDeque<Order>>,
    sells: BTreeMap<u32, VecDeque<Order>>,
}

/// A trade: the 2 orders, the price of the one that was waiting, and how
/// much changed hands.
struct Trade {
    incoming: u32,
    waiting: u32,
    price: u32,
    quantity: u32,
}

impl Book {
    /// The best waiting order that the incoming order can trade with: the
    /// lowest price for a buyer and the highest for a seller, and the
    /// oldest order at that price.
    fn best(&mut self, order: Order) -> Option<&mut VecDeque<Order>> {
        let (price, queue) = match order.side {
            Side::Buy => self.sells.iter_mut().next()?,
            Side::Sell => self.buys.iter_mut().next_back()?,
        };
        let acceptable = match order.side {
            Side::Buy => *price <= order.price,
            Side::Sell => *price >= order.price,
        };

        acceptable.then_some(queue)
    }

    /// Trades the order against the book for as long as prices meet, and
    /// leaves what remains of it waiting in the book.
    fn submit(&mut self, mut order: Order) -> Vec<Trade> {
        let mut trades = Vec::new();

        while order.quantity > 0 {
            let Some(queue) = self.best(order) else {
                break;
            };
            let Some(waiting) = queue.front_mut() else {
                break;
            };
            let quantity = order.quantity.min(waiting.quantity);

            trades.push(Trade {
                incoming: order.id,
                waiting: waiting.id,
                price: waiting.price,
                quantity,
            });
            order.quantity -= quantity;
            waiting.quantity -= quantity;

            if waiting.quantity == 0 {
                queue.pop_front();
            }

            self.buys
                .retain(|_price, queue| !queue.is_empty());
            self.sells
                .retain(|_price, queue| !queue.is_empty());
        }

        if order.quantity > 0 {
            let side = match order.side {
                Side::Buy => &mut self.buys,
                Side::Sell => &mut self.sells,
            };

            side.entry(order.price)
                .or_default()
                .push_back(order);
        }

        trades
    }

    fn describe(side: &BTreeMap<u32, VecDeque<Order>>) -> String {
        let levels: Vec<String> = side
            .iter()
            .map(|(price, queue)| {
                let quantity: u32 = queue
                    .iter()
                    .map(|order| order.quantity)
                    .sum();

                format!("{quantity} at {price}")
            })
            .collect();

        match levels.is_empty() {
            true => "nothing".to_owned(),
            false => levels.join(", "),
        }
    }
}
// ANCHOR_END: book

// ANCHOR: main
fn main() {
    let orders = [
        (Side::Sell, 1010, 50),
        (Side::Sell, 1005, 30),
        (Side::Sell, 1005, 40),
        (Side::Buy, 1000, 60),
        (Side::Buy, 1005, 50),
        (Side::Buy, 1010, 100),
        (Side::Sell, 995, 80),
    ];
    let mut book = Book::default();
    let mut traded = 0;

    for (number, (side, price, quantity)) in (1..).zip(orders) {
        let verb = match side {
            Side::Buy => "buy",
            Side::Sell => "sell",
        };
        let order = Order {
            id: number,
            side,
            price,
            quantity,
        };

        println!("order {number}: {verb} {quantity} at {price}");

        for trade in book.submit(order) {
            traded += trade.quantity;
            println!(
                "    trade: {} at {}, order {} with waiting order {}",
                trade.quantity, trade.price, trade.incoming, trade.waiting
            );
        }
    }

    println!("waiting to buy: {}", Book::describe(&book.buys));
    println!("waiting to sell: {}", Book::describe(&book.sells));
    println!("shares traded: {traded}");
}
// ANCHOR_END: main
