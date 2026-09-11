//! Virtual memory arithmetic: address to page and offset, page counts, and how a
//! page fault is classified.
//!
//! Run with: cargo run --bin os_paging

const PAGE_SIZE: u64 = 4096;

fn split_page(address: u64) -> (u64, u64) {
    (address / PAGE_SIZE, address % PAGE_SIZE)
}

fn pages_needed(bytes: u64) -> u64 {
    bytes.div_ceil(PAGE_SIZE)
}

#[derive(Debug, PartialEq, Eq)]
enum Fault {
    /// The page is resident; a copy-on-write write or permission upgrade.
    Minor,
    /// The mapping is valid but the page must be read from backing store.
    Major,
    /// The mapping is valid and resident, but the access permission is wrong.
    Protection,
    /// No valid mapping at this address.
    Invalid,
}

fn classify_fault(mapped: bool, present: bool, writable: bool) -> Fault {
    match (mapped, present, writable) {
        (false, _, _) => Fault::Invalid,
        (true, false, _) => Fault::Major,
        (true, true, false) => Fault::Protection,
        (true, true, true) => Fault::Minor,
    }
}

fn main() {
    println!("page size: {PAGE_SIZE} bytes");

    println!("\naddress -> page, offset");
    for address in [0u64, 0x1234, 0x1fff, 0x2000] {
        let (page, offset) = split_page(address);
        println!("  0x{address:04x} -> page {page:>2}, offset 0x{offset:03x}");
    }

    println!("\npages needed");
    for bytes in [0u64, 1, PAGE_SIZE, PAGE_SIZE + 1] {
        println!("  {bytes:>5} bytes -> {}", pages_needed(bytes));
    }

    println!("\nfault classification");
    println!(
        "  unmapped           -> {:?}",
        classify_fault(false, false, false)
    );
    println!(
        "  mapped, not in ram -> {:?}",
        classify_fault(true, false, true)
    );
    println!(
        "  resident, read-only-> {:?}",
        classify_fault(true, true, false)
    );
    println!(
        "  resident, writable -> {:?}",
        classify_fault(true, true, true)
    );

    assert_eq!(split_page(0x1234), (1, 0x234));
    assert_eq!(pages_needed(0), 0);
    assert_eq!(pages_needed(PAGE_SIZE + 1), 2);
    assert_eq!(classify_fault(true, false, true), Fault::Major);
    assert_eq!(classify_fault(true, true, false), Fault::Protection);
    assert_eq!(classify_fault(false, true, true), Fault::Invalid);

    println!("\nall checks passed");
}
