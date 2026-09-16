# References {#references}

## How to read this list

Sources are grouped by kind, and each entry says where the claim it supports
appears. Language and library claims cite the document that specifies the
behaviour: the *Rust Reference* for the language, the standard library
documentation for a function, and the *Rust Book* for a mechanism. Algorithm
claims cite a textbook or the paper that introduced the algorithm. Quotations are
attributed to the person who wrote them, with the work they appear in, and the
list is in alphabetical order by surname.

## Language and library documentation

- **The Rust Book.** The Rust Project Developers. <https://doc.rust-lang.org/book/>.
  Cited for monomorphisation (Chapter 1), enumerations (Chapter 7), boxes
  (Chapters 7, 14), `Rc` and `RefCell` (Chapter 16), shadowing and mutability
  (Chapter 25), and command-line arguments (Chapter 29).
- **The Rust Reference.** The Rust Project Developers.
  <https://doc.rust-lang.org/reference/>. Cited for names and scopes (Chapter 25).
- **The Rustonomicon.** The Rust Project Developers.
  <https://doc.rust-lang.org/nomicon/>. Cited for the rules an `unsafe` block
  relies on (Chapters 24, 33).
- **Rust API Guidelines.** The Rust Project Developers.
  <https://rust-lang.github.io/api-guidelines/>. Cited for documentation requirements
  and for the naming of conversion methods.
- **Standard library documentation.** The Rust Project Developers.
  <https://doc.rust-lang.org/std/>. Individual items are cited in each chapter's
  reference list, including `HashMap`, `VecDeque`, `BinaryHeap`, `Reverse`, `Rc`,
  `Weak`, `RefCell`, `Mutex`, `Condvar`, `PoisonError`, `Instant`, `Duration`,
  `Box`, `Option`, `JoinHandle`, `fs`, `OpenOptions`, `BufReader`, `Path`,
  `PathBuf`, `ErrorKind`, `String::as_mut_vec`, `thread::scope`, `black_box`,
  `sort_unstable_by_key`, `clear_poison`, and `try_reserve`.
- **Clippy lint documentation.** The Rust Project Developers.
  <https://rust-lang.github.io/rust-clippy/master/>. Cited for `new_without_default`
  (Chapter 15).
- **The `libc` crate.** <https://docs.rs/libc/>. Cited for `getpid` (Chapter 24).

## Papers and books

- **Bellman, Richard.** *Dynamic Programming*. Princeton University Press, 1957.
  The origin of the method used in Chapter 12.
- **Cormen, Thomas H., Charles E. Leiserson, Ronald L. Rivest, and Clifford
  Stein.** *Introduction to Algorithms*, 4th edition. MIT Press, 2022. Cited for
  binary search trees (Chapter 8), dynamic programming (Chapters 12, 13), breadth-
  first search (Chapter 23), priority queues (Chapter 32), and topological sort
  (Chapter 11).
- **Fredkin, Edward.** "Trie memory". *Communications of the ACM* 3(9), 1960,
  pages 490–499. The paper that introduced the structure in Chapter 10.
- **Hoare, C. A. R.** "Null References: The Billion Dollar Mistake". Presentation
  at QCon London, 2009. The source of the phrasing used in Chapter 12 for the
  choice between a sentinel and `Option`.
- **Kahn, Arthur B.** "Topological sorting of large networks". *Communications of
  the ACM* 5(11), 1962, pages 558–562. The algorithm in Chapters 11 and 65.
- **Knuth, Donald E.** "Structured Programming with go to Statements". *ACM
  Computing Surveys* 6(4), 1974, pages 261–301. The source of the observation about
  premature optimisation, including the qualification that summaries of it usually
  leave out.
- **Knuth, Donald E.** *The Art of Computer Programming*, Volume 3: *Sorting and
  Searching*, 2nd edition. Addison-Wesley, 1998. Cited for digital searching
  (Chapter 10).
- **Lamport, Leslie.** "Distribution". Letter, 1987; collected in *Distributed
  Systems*, 2nd edition, 1993. The source of the sentence about partial failure
  quoted in Chapter 22.
- **Patterson, David A.** "Latency lags bandwidth". *Communications of the ACM*
  47(10), 2004, pages 71–75. The source of the phrasing quoted in Chapter 24.
- **Perlis, Alan J.** "Epigrams on Programming". *ACM SIGPLAN Notices* 17(9), 1982,
  pages 7–13.
- **Stroustrup, Bjarne.** "Foundations of C++". Keynote, *Proceedings of the 2012
  European Conference on Object-Oriented Programming (ECOOP)*, 2012. The source of
  the two-part statement of the zero-overhead principle quoted at the opening of
  the preface.
- **Wirth, Niklaus.** "A Plea for Lean Software". *IEEE Computer* 28(2), 1995,
  pages 64–68.

## Quotations in this book

Four sentences are quoted from other people, each in a place where the quotation
states something the surrounding chapter then uses.

| Where | Quotation | Source |
|---|---|---|
| Preface | The two-part statement of the zero-overhead principle | Stroustrup, *Foundations of C++*, 2012 |
| Chapter 12 | Null references as a mistake that has cost a great deal | Hoare, QCon London, 2009 |
| Chapter 22 | A distributed system as one in which a machine you did not know about can stop yours | Lamport, "Distribution", 1987 |
| Chapter 24 | "Latency lags bandwidth" | Patterson, *Communications of the ACM*, 2004 |

Each quotation is short, is attributed in the chapter where it appears, and is
quoted from the work named here. Nothing attributed to anyone in this book is a
paraphrase presented as a quotation.
