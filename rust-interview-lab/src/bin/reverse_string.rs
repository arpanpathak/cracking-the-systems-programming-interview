
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

}