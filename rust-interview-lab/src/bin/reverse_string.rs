
fn reverse_str(s: &mut String) {
    // SAFETY: s._as_mut_vec() is unsafe because it exposes the inner mutability to it's character buffer, and we must ensure
    // to leave valid UTF-8. We enforce ASCII only characters.
    assert!(s.is_ascii());
    let bytes = unsafe { s.as_mut_vec() };

    let (mut start, mut end) = (0, bytes.len() - 1);

    while start < end {
        bytes.swap(start, end);
        start+=1; end-=1;
    }
}

fn main() {
    for value in ["abcd", "abc", "a", "rust"] {
        let mut s = String::from(value);
        reverse_str(&mut s);
        println!("{value:>6} -> {s}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_even_length_string_is_reversed() {
        let mut s = String::from("abcd");
        reverse_str(&mut s);
        assert_eq!(s, "dcba");
    }

    #[test]
    fn an_odd_length_string_keeps_its_middle_byte() {
        let mut s = String::from("abc");
        reverse_str(&mut s);
        assert_eq!(s, "cba");
    }

    #[test]
    fn a_single_byte_is_unchanged() {
        let mut s = String::from("a");
        reverse_str(&mut s);
        assert_eq!(s, "a");
    }

    #[test]
    fn the_buffer_is_reused() {
        let mut s = String::from("abcd");
        let capacity = s.capacity();
        let address = s.as_ptr();
        reverse_str(&mut s);
        assert_eq!(s.capacity(), capacity);
        assert_eq!(s.as_ptr(), address);
    }

    #[test]
    fn reversing_twice_restores_the_string() {
        let mut s = String::from("interview");
        reverse_str(&mut s);
        reverse_str(&mut s);
        assert_eq!(s, "interview");
    }

    #[test]
    #[should_panic]
    fn non_ascii_input_panics() {
        let mut s = String::from("café");
        reverse_str(&mut s);
    }
}
