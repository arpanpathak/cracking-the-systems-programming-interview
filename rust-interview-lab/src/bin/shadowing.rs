// ============================================================================
// Variable shadowing vs mutation
//
// Ported from the Rust playground repo (`shadowing.rs`).
//
// What this demonstrates:
//   - Rust allows a new `let` binding with the same name as an existing
//     binding. This is called **shadowing**.
//   - Shadowing can change the value *and the type* of a variable without
//     declaring it `mut`.
//   - The old binding is no longer reachable after the shadowing `let`.
//
// Why this appears in interviews:
//   - Rust SDK code often shadows parsed/deserialized values to convert them
//     from raw input to typed domain values:
//
//       let raw = request.header("X-GPU-Count")?;
//       let raw: u64 = raw.parse()?;   // shadow with a typed value
//
//   - Shadowing is also useful after unwrapping an `Option`/`Result` when the
//     guard value is no longer needed.
//
// Run:
//   cargo run --bin shadowing
// ============================================================================

fn demonstrate_shadowing() -> String {
    // First binding is an integer.
    let value: u32 = 7;
    let mut log = format!("integer: {value}");

    // Shadow the integer with a String. The old integer is gone.
    let value = value.to_string();
    log.push_str(&format!("\nstring: {value}"));

    // Shadow the String with a usize computed from it.
    let value = value.len();
    log.push_str(&format!("\nusize: {value}"));

    log
}

fn demonstrate_mutation() -> String {
    // If you need to mutate the same binding's value (same type) without
    // creating a new binding, mark it `mut`.
    let mut count = 0;
    let mut log = String::from("mut count:");
    for _ in 0..3 {
        count += 1;
        log.push_str(&format!(" {count}"));
    }
    log
}

fn main() {
    println!("=== Shadowing ===");
    println!("{}", demonstrate_shadowing());

    println!("\n=== Mutation ===");
    println!("{}", demonstrate_mutation());
}

// ============================================================================
// Tests (cargo test --bin shadowing)
// ============================================================================
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shadowing_allows_type_changes() {
        let log = demonstrate_shadowing();
        assert!(log.contains("integer: 7"));
        assert!(log.contains("string: 7"));
        assert!(log.contains("usize: 1"));
    }

    #[test]
    fn mutation_requires_mut_binding() {
        let log = demonstrate_mutation();
        assert!(log.contains("mut count: 1 2 3"));
    }
}
