//! Valid Parentheses: classic stack problem with idiomatic pattern matching.
//!
pub fn is_valid(s: &str) -> bool {
    use std::collections::HashMap;

    let mut stack = Vec::with_capacity(s.len());

    // Maps each closing delimiter to the opening delimiter it must match.
    let expected = HashMap::from([(')', '('), ('}', '{'), (']', '[')]);

    for ch in s.chars() {
        match ch {
            '(' | '[' | '{' => stack.push(ch),
            // Every other character, including one outside the six delimiters,
            // must close the top of the stack.
            _ => {
                if stack.pop().as_ref() != expected.get(&ch) {
                    return false;
                }
            }
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
