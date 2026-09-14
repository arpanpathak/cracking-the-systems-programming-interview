use std::cmp::Reverse;
use std::collections::BinaryHeap;

#[derive(Default)]
pub struct MedianFinder {
    low: BinaryHeap<i32>,
    high: BinaryHeap<Reverse<i32>>,
}

impl MedianFinder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_num(&mut self, num: i32) {
        self.low.push(num);

        if let Some(val) = self.low.pop() {
            self.high.push(Reverse(val));
        }

        if self.high.len() > self.low.len() {
            if let Some(Reverse(val)) = self.high.pop() {
                self.low.push(val);
            }
        }
    }

    pub fn find_median(&self) -> Option<f64> {
        let max_low = *self.low.peek()?;

        if self.low.len() > self.high.len() {
            Some(max_low as f64)
        } else {
            let Reverse(min_high) = *self.high.peek()?;
            Some((max_low as f64 + min_high as f64) / 2.0)
        }
    }
}

const SAMPLE: [i32; 11] = [6, 10, 2, 6, 5, 0, 6, 3, 1, 0, 0];

fn main() {
    let mut finder = MedianFinder::new();

    for value in SAMPLE {
        finder.add_num(value);
        match finder.find_median() {
            Some(median) => println!("after {value:>2}: median {median}"),
            None => println!("after {value:>2}: no median"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The median of a sorted slice, computed directly.
    fn median_of_sorted(values: &[i32]) -> f64 {
        let middle = values.len() / 2;
        if values.len() % 2 == 1 {
            values[middle] as f64
        } else {
            (values[middle - 1] as f64 + values[middle] as f64) / 2.0
        }
    }

    #[test]
    fn an_empty_finder_has_no_median() {
        assert_eq!(MedianFinder::new().find_median(), None);
    }

    #[test]
    fn one_value_is_the_median() {
        let mut finder = MedianFinder::new();
        finder.add_num(7);
        assert_eq!(finder.find_median(), Some(7.0));
    }

    #[test]
    fn an_even_count_averages_the_middle_two() {
        let mut finder = MedianFinder::new();
        finder.add_num(1);
        finder.add_num(2);
        assert_eq!(finder.find_median(), Some(1.5));
    }

    #[test]
    fn three_values_are_ordered() {
        let mut finder = MedianFinder::new();
        for (value, median) in [1, 2, 3].into_iter().zip([1.0, 1.5, 2.0]) {
            finder.add_num(value);
            assert_eq!(finder.find_median(), Some(median));
        }
    }

    #[test]
    fn duplicates_are_kept() {
        let mut finder = MedianFinder::new();
        for value in [4, 4, 4, 4] {
            finder.add_num(value);
        }
        assert_eq!(finder.find_median(), Some(4.0));
    }

    #[test]
    fn the_stream_matches_a_sort_on_every_step() {
        let mut finder = MedianFinder::new();
        let mut seen = Vec::new();

        for value in SAMPLE {
            finder.add_num(value);
            seen.push(value);
            seen.sort_unstable();

            assert_eq!(finder.find_median(), Some(median_of_sorted(&seen)));
        }
    }

    #[test]
    fn the_two_heaps_never_differ_by_more_than_one() {
        let mut finder = MedianFinder::new();

        for value in SAMPLE {
            finder.add_num(value);
            assert!(finder.low.len().abs_diff(finder.high.len()) <= 1);
        }
    }
}
