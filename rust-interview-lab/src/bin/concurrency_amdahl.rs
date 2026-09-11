//! Amdahl's law: the serial fraction of the work caps the speedup from adding
//! processors. A program that is 50 percent serial cannot go faster than 2x, no
//! matter how many cores it gets.
//!
//! Run with: cargo run --bin concurrency_amdahl

/// Speedup with `processors` when `serial` is the non-parallel fraction.
fn speedup(serial: f64, processors: f64) -> f64 {
    1.0 / (serial + (1.0 - serial) / processors)
}

fn main() {
    let processor_counts = [1.0, 2.0, 4.0, 8.0, 16.0];
    let serial_fractions = [0.0, 0.05, 0.10, 0.25, 0.50];

    print!("{:>8} |", "serial");
    for processors in processor_counts {
        print!(" {processors:>6.0}");
    }
    println!("   <- processors");
    println!("{:->9}+{}", "", "-".repeat(7 * processor_counts.len()));

    for serial in serial_fractions {
        print!("{serial:>8.2} |");
        for processors in processor_counts {
            print!(" {:>6.2}", speedup(serial, processors));
        }
        println!();
    }

    println!("\nlimit as processors grow: 1 / serial");
    for serial in serial_fractions {
        let limit = if serial == 0.0 {
            f64::INFINITY
        } else {
            1.0 / serial
        };
        println!("  {serial:>4.2} -> {limit:>6.1}");
    }

    assert!((speedup(0.0, 4.0) - 4.0).abs() < 1e-9);
    assert!((speedup(0.5, 4.0) - 1.6).abs() < 1e-9);
    assert!(speedup(0.5, 16.0) < 1.9, "2x is the ceiling for 50% serial");

    println!("\nall checks passed");
}
