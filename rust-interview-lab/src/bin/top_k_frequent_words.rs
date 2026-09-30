use std::{
    cmp::Reverse as Rev,
    collections::{BinaryHeap, HashMap},
};

/// Returns vec!<(word, frequency)>, most frequent first.
fn top_k_frequent(sentence: &str, k: usize) -> Vec<(String, u32)> {
    // Split string by white spaces. Map it and trim any non alphanumeric characters. Finally,
    // filter all the empty strings and map everything to lowercase characters.
    let words: Vec<String> = sentence
        .split_whitespace()
        .map(|w| w.trim_matches(|c: char| !c.is_alphanumeric()))
        .filter(|w| !w.is_empty())
        .map(str::to_lowercase)
        .collect();

    // Build the frequency map...
    let mut frequencies = HashMap::<&str, u32>::new();
    for word in &words {
        *frequencies.entry(word.as_str()).or_default() += 1;
    }

    // Keep a min heap of size k. Reverse flips the max heap, so the least
    // frequent word sits on top and gets popped once we go over k.
    let mut min_heap = BinaryHeap::<Rev<(u32, &str)>>::new();
    for (&word, &frequency) in &frequencies {
        min_heap.push(Rev((frequency, word)));
        if min_heap.len() > k {
            min_heap.pop();
        }
    }

    // Ascending order of Reverse means most frequent first.
    min_heap
        .into_sorted_vec()
        .into_iter()
        .map(|Rev((frequency, word))| (word.to_string(), frequency))
        .collect()
}

fn main() {
    let sentence = r"This is a short sentence. We'll count words.
    Let us count words in this sentence
    ";

    let top_k = top_k_frequent(sentence, 3);
    println!("Top 3 frequency [(word, frequency)] : \n {:#?}", top_k);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn picks_most_frequent() {
        let result = top_k_frequent("a a a b b c", 2);
        assert_eq!(result, vec![("a".to_string(), 3), ("b".to_string(), 2)]);
    }

    #[test]
    fn ignores_case_and_punctuation() {
        let result = top_k_frequent("Hello, hello! HELLO world.", 1);
        assert_eq!(result, vec![("hello".to_string(), 3)]);
    }

    #[test]
    fn k_larger_than_word_count() {
        assert_eq!(top_k_frequent("x y", 10).len(), 2);
    }

    #[test]
    fn empty_input() {
        assert!(top_k_frequent("", 3).is_empty());
    }
}
