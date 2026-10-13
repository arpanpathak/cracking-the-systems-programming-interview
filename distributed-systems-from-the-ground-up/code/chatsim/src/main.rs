//! Command chatsim sends chat messages to a phone that goes offline for a
//! while. Every message in a conversation has a number. The phone says
//! which number it has reached, and the server sends what comes after.
//!
//! Run it from code/ with:
//!
//!     cargo run -p chatsim

// ANCHOR: imports
use std::cmp::Ordering;
// ANCHOR_END: imports

// ANCHOR: server
/// A conversation on the server: every message, in the order it arrived.
/// The number of a message is its position, starting from 1.
struct Conversation {
    messages: Vec<String>,
}

impl Conversation {
    /// Stores a message and returns its number.
    fn send(&mut self, text: &str) -> usize {
        self.messages.push(text.to_owned());

        self.messages.len()
    }

    /// The messages after number `received`, with their numbers.
    fn after(&self, received: usize) -> impl Iterator<Item = (usize, &String)> {
        self.messages
            .iter()
            .enumerate()
            .skip(received)
            .map(|(index, text)| (index + 1, text))
    }
}
// ANCHOR_END: server

// ANCHOR: phone
/// A phone. It remembers the number of the last message it has shown.
struct Phone {
    received: usize,
}

impl Phone {
    /// Takes a message from the server. A message it already has, or one
    /// that would leave a gap, is not shown.
    fn deliver(&mut self, number: usize, text: &str) {
        let expected = self.received + 1;

        match number.cmp(&expected) {
            Ordering::Less => println!("  phone ignores {number}: already shown"),
            Ordering::Greater => {
                println!("  phone ignores {number}: message {expected} is missing")
            }
            Ordering::Equal => {
                self.received = number;
                println!("  phone shows {number}: {text}");
            }
        }
    }

    /// Asks the server for everything after the last message shown.
    fn sync(&mut self, conversation: &Conversation) {
        for (number, text) in conversation.after(self.received) {
            self.deliver(number, text);
        }
    }
}
// ANCHOR_END: phone

// ANCHOR: main
fn main() {
    let mut conversation = Conversation {
        messages: Vec::new(),
    };
    let mut phone = Phone { received: 0 };

    println!("the phone is online");
    let first = conversation.send("are you coming?");
    phone.deliver(first, "are you coming?");

    println!("the phone loses its connection, and 3 messages are sent");
    for text in ["hello?", "we are starting", "table 4"] {
        let number = conversation.send(text);
        println!("  server stores {number}: {text}");
    }

    println!("message 4 reaches the phone alone, over a connection that drops again");
    phone.deliver(4, "table 4");

    println!(
        "the phone reconnects and reports that it has message {}",
        phone.received
    );
    phone.sync(&conversation);

    println!("the server repeats message 3, because an acknowledgement was lost");
    phone.deliver(3, "we are starting");

    println!(
        "messages on the server: {}, shown on the phone: {}",
        conversation.messages.len(),
        phone.received
    );
}
// ANCHOR_END: main
