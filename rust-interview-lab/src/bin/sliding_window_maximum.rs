use std::collections::VecDeque;

// 0,1,2,3,4,5
fn sliding_window_max(s: &[i32], k: usize) -> Vec<i32> {
    let mut dq = VecDeque::new();
    let mut out = vec![];

    for (i, &x) in s.iter().enumerate() {
        // Slide out of the invalid or we could say that f <= i - k, because Window starts from (i - k, i]
        if dq.front().is_some_and(|&f| f + k <= i) {
            dq.pop_front();
        }

        while dq
            .back()
            .is_some_and(|&back_idx| s[back_idx] <= x)
        {
            dq.pop_back();
        }
        dq.push_back(i);

        if i + 1 >= k {
            out.push(s[dq[0]]);
        }
    }

    out
}

fn main() {
    let values = [1, 3, -1, -3, 5, 3, 6, 7];

    println!("{:?}", sliding_window_max(&values, 3));
}
