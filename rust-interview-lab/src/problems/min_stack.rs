//! Min Stack: O(1) push, pop, top, and get_min.
//!
//! We keep a parallel `mins` stack. Each push stores the current minimum at that
//! point in history, so pop is symmetric.

#[derive(Debug, Default)]
pub struct MinStack {
    values: Vec<i32>,
    mins: Vec<i32>,
}

impl MinStack {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn push(&mut self, val: i32) {
        match self.mins.last() {
            Some(&min) if min <= val => self.mins.push(min),
            _ => self.mins.push(val),
        }
        self.values.push(val);
    }

    pub fn pop(&mut self) -> Option<i32> {
        self.mins.pop();
        self.values.pop()
    }

    pub fn top(&self) -> Option<i32> {
        self.values.last().copied()
    }

    pub fn get_min(&self) -> Option<i32> {
        self.mins.last().copied()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stack_tracks_minimum() {
        let mut stack = MinStack::new();
        stack.push(-2);
        stack.push(0);
        stack.push(-3);
        assert_eq!(stack.get_min(), Some(-3));
        assert_eq!(stack.pop(), Some(-3));
        assert_eq!(stack.top(), Some(0));
        assert_eq!(stack.get_min(), Some(-2));
    }

    #[test]
    fn handles_duplicates() {
        let mut stack = MinStack::new();
        stack.push(1);
        stack.push(1);
        stack.pop();
        assert_eq!(stack.get_min(), Some(1));
    }
}
