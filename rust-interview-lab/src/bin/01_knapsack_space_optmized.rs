use std::{ 
    cmp::max, mem::swap 
};

struct Item {
    weight: usize,
    value: i32,
}

fn main() {
    let capacity = 10;
    let items = vec![
        Item { weight: 10, value: 60 },
        Item { weight: 20, value: 100 },
        Item { weight: 30, value: 120 },
    ];

    println!("Max value: {}", solve(capacity, &items));
}

fn solve(capacity: usize, items: &[Item]) -> i32 {
    let n = items.len();
    
    // Initialize two rows
    let mut prev = vec![0; capacity + 1];
    let mut curr = vec![0; capacity + 1];

    for item in items.iter() {
        // let item = &items[i];
        for w in 0..=capacity {
            curr[w] = match item.weight > w {
                true => prev[w],
                false => max(prev[w - item.weight] + item.value, prev[w])
            };
        }
        // SWAP prev and curr instead of assigning.
        // This exchanges the data so 'curr' is ready for the next iteration.
        swap(&mut prev, &mut curr);
    }

    // 'prev' now holds the final row after the last swap
    prev[capacity]
}
