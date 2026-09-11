# Benchmarking examples

Runnable programs that measure the data structures in `lists/` and `cache/`, which
sit beside them in this directory.

| Program | Run | What it does |
|---|---|---|
| `benchmark.rs` | `cargo run --release --bin benchmark` | The single main: the cache benchmark, then all four list variants |
| `list_box.rs` | `cargo run --bin list_box` | Demo of `lists::boxed` |
| `list_enum.rs` | `cargo run --bin list_enum` | Demo of `lists::enum_node` |
| `list_drop.rs` | `cargo run --release --bin list_drop` | Demo of `lists::boxed_drop`: 5,000,000 nodes, freed iteratively |

## Subcommands

```bash
cargo run --release --bin benchmark                      # cache, then lists
cargo run --release --bin benchmark cache                # arena vs Rc<RefCell> list
cargo run --release --bin benchmark list                 # all four variants
cargo run --release --bin benchmark list enum 500000     # one variant, one size
cargo run --release --bin benchmark list box+drop 5000000
```

## Layout

The implementations in `lists/` and `cache/` are declared as library modules by
`src/lib.rs`, using a `#[path]` attribute that points to this directory. The
sources therefore sit with the programs that measure them, while all four programs
link one compiled copy.

Each program declaring `mod lists;` for itself would be an alternative, but an
unused `pub` item in a Cargo binary is reported as dead code, so three of the four
variants would be dead in every program that does not use them, and the shared code
would be compiled four times.

## Measurement notes

Timings are single-threaded and taken in release mode. Each measurement is
preceded by a warm-up pass and reported as the fastest of three passes; a first
pass over a fresh heap measured between 2.3 ms and 11.4 ms for one push loop of
fixed size. Recorded output is in `../BENCHMARKS.md`.

## Report

[`benchmarking-report.pdf`](benchmarking-report.pdf) presents this work as a
journal-style paper: abstract, introduction, background, method, results,
discussion, threats to validity, and references. It is built from
`benchmarking-report.md`.

```bash
python3 benchmarking_examples/build_report_pdf.py   # writes benchmarking-report.pdf
```

The build needs `markdown`, `pygments`, and `weasyprint`.
