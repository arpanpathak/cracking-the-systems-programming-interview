use std::{cmp::Reverse, collections::BTreeMap};

#[derive(Eq, PartialEq, Ord, PartialOrd)]
enum Event {
    Start(Reverse<i32>),
    End(i32),
}

fn get_skyline(buildings: &[[i32; 3]]) -> Vec<[i32; 2]> {
    let mut events: Vec<(i32, Event)> = buildings
        .iter()
        .flat_map(|&[left, right, height]| {
            [
                (left, Event::Start(Reverse(height))),
                (right, Event::End(height)),
            ]
        })
        .collect();

    events.sort_unstable();

    let mut active = BTreeMap::from([(0, 1)]);
    let mut skyline = Vec::new();
    let mut prev_max = 0;

    for (x, event) in events {
        match event {
            Event::Start(Reverse(h)) => *active.entry(h).or_default() += 1,
            Event::End(h) => {
                let count = active.entry(h).or_default();
                *count -= 1;

                if *count == 0 {
                    active.remove(&h);
                }

                // OR
                // if active.get_mut(&h).is_some_and(|c| { *c -= 1; *c == 0 }) {
                //    active.remove(&h);
                // }
            }
        }

        if let Some(&curr_max) = active.keys().next_back()
            && curr_max != prev_max
        {
            skyline.push([x, curr_max]);
            prev_max = curr_max;
        }
    }

    skyline
}

fn main() {
    let buildings = [
        [2, 9, 10],
        [3, 7, 15],
        [5, 12, 12],
        [15, 20, 10],
        [19, 24, 8],
    ];

    println!("{:?}", get_skyline(&buildings));
}
