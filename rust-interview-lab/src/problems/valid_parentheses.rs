//! Valid Parentheses: classic stack problem with idiomatic pattern matching.
//!
pub fn is_valid(s: &str) -> bool {
    use std::collections::HashMap;

    let mut stack = Vec::with_capacity(s.len());

    // Because manually adding if else is not an extensible solution.
    let expected = HashMap::from([
        (')', '('), 
        ('}', '{'), 
        (']', '['),
        // You can write whatever grammar you'd like, such as '<', '|', '$'....
    ]);

    for ch in s.chars() {
        // Look at the tasteful thickness of "পূর্ণাঙ্গ বিন্যাস মিলকরণ", We love Unicode!
        match ch {
            '(' | '[' | '{' => stack.push(ch),
            // Rust compiler will throw error for not handling all the possible character ranges.
            // So ask it to chill with an if guard.....I've got you Sir!! Thank 
            _ => { if stack.pop().as_ref() != expected.get(&ch) { return false; } }
        }
    }

    stack.is_empty()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valid_cases() {
        assert!(is_valid("()"));
        assert!(is_valid("()[]{}"));
        assert!(is_valid("{[()]}"));
    }

    #[test]
    fn invalid_cases() {
        assert!(!is_valid("(]"));
        assert!(!is_valid("([)]"));
        assert!(!is_valid("("));
        assert!(!is_valid(")"));
        assert!(!is_valid("(("));
    }

    
}
