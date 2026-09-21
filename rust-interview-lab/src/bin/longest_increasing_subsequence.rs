use std::collections::BTreeSet;

// TODO: Practice iterating over slice reference, BTreeSet. And also,BTreeMap...
fn lis_len(nums: &[i32]) -> usize {
    let mut tails = BTreeSet::new();

    for &num in nums {
        if let Some(&ceiling) = tails.range(num..).next() {
            tails.remove(&ceiling);
        }
        tails.insert(num);
    }

    tails.len()
}

fn main() {
    println!("{}", lis_len(&[10, 9, 2, 5, 3, 7, 101, 18])); // 4
    println!("{}", lis_len(&[0, 1, 0, 3, 2, 3]));           // 4
    println!("{}", lis_len(&[7, 7, 7, 7]));                 // 1
    println!("{}", lis_len(&[5, 4, 3, 2, 1]));              // 1
    println!("{}", lis_len(&[1, 2, 3, 4, 5]));              // 5
    println!("{}", lis_len(&[]));                           // 0
}
