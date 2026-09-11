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

fn main() {
    todo!("TODO TODO")
}