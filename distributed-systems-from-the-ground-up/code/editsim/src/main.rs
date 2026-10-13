//! Command editsim lets 2 people change the text "cat" at the same moment.
//! It applies their changes in 3 ways: as they are, with the position of the
//! second change adjusted for the first, and with a name for every
//! character in place of a position.
//!
//! Run it from code/ with:
//!
//!     cargo run -p editsim

// ANCHOR: imports
use std::collections::BTreeMap;
// ANCHOR_END: imports

// ANCHOR: positions
/// A change: put a character at a position, counted from 0.
#[derive(Clone, Copy)]
struct Insert {
    at: usize,
    character: char,
}

fn apply(text: &str, change: Insert) -> String {
    let (before, after) = text.split_at(change.at.min(text.len()));

    format!("{before}{}{after}", change.character)
}

/// Adjusts a change that was made without knowledge of `earlier`, so that
/// it still lands where its author meant it. `wins_ties` decides which of 2
/// characters put at the same position comes first.
fn transform(change: Insert, earlier: Insert, wins_ties: bool) -> Insert {
    let shifted = earlier.at < change.at || (earlier.at == change.at && !wins_ties);

    Insert {
        at: change.at + usize::from(shifted),
        ..change
    }
}
// ANCHOR_END: positions

// ANCHOR: names
/// A text in which every character has a name that no other character has:
/// a place between its neighbours, and the device that typed it. The text
/// is the characters in the order of their names.
#[derive(Clone, Default)]
struct Named {
    characters: BTreeMap<(u32, u8), char>,
}

impl Named {
    fn insert(&mut self, place: u32, device: u8, character: char) {
        self.characters
            .insert((place, device), character);
    }

    fn text(&self) -> String {
        self.characters.values().collect()
    }
}
// ANCHOR_END: names

// ANCHOR: main
fn main() {
    let start = "cat";
    let ada = Insert {
        at: 1,
        character: 'h',
    };
    let bob = Insert {
        at: 3,
        character: 's',
    };

    println!("both start from \"{start}\". ada puts h at 1, bob puts s at 3");

    let at_ada = apply(&apply(start, ada), bob);
    let at_bob = apply(&apply(start, bob), ada);
    println!("changes applied as they are:     ada sees \"{at_ada}\", bob sees \"{at_bob}\"");

    let at_ada = apply(&apply(start, ada), transform(bob, ada, false));
    let at_bob = apply(&apply(start, bob), transform(ada, bob, true));
    println!("positions adjusted:              ada sees \"{at_ada}\", bob sees \"{at_bob}\"");

    // c, a and t are at places 1000, 2000 and 3000.
    let mut base = Named::default();
    [(1000, 'c'), (2000, 'a'), (3000, 't')]
        .into_iter()
        .for_each(|(place, character)| base.insert(place, 0, character));

    let (mut at_ada, mut at_bob) = (base.clone(), base.clone());
    at_ada.insert(1500, 1, 'h');
    at_ada.insert(4000, 2, 's');
    at_bob.insert(4000, 2, 's');
    at_bob.insert(1500, 1, 'h');
    println!(
        "a name for every character:      ada sees \"{}\", bob sees \"{}\"",
        at_ada.text(),
        at_bob.text()
    );

    // Both put a character at the same place, between a and t.
    let (mut at_ada, mut at_bob) = (base.clone(), base);
    at_ada.insert(2500, 1, 'r');
    at_ada.insert(2500, 2, 'n');
    at_bob.insert(2500, 2, 'n');
    at_bob.insert(2500, 1, 'r');
    println!(
        "both type between a and t:       ada sees \"{}\", bob sees \"{}\"",
        at_ada.text(),
        at_bob.text()
    );
}
// ANCHOR_END: main
