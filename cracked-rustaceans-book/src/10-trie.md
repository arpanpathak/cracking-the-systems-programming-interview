# 10. Trie {#trie}

*Source file: [`src/problems/trie.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/trie.rs). Test it with `cargo test trie`.*

## Problem Statement

Store a set of strings so that two questions are cheap: whether an exact string is
present, and whether any stored string begins with a given prefix. A hash map answers
the first in constant time and the second only by scanning every key, which is the
reason for the structure.

## Designing a Solution

Each node holds a map from a character to a child node, plus a flag saying whether the
path that ends at this node spells a stored string. A string is present when walking
its characters from the root succeeds and the final node has the flag set.

```text
words: "gpu", "gpucloud"

           (root)
              |
              g
              |
              p
              |
              u   <- terminal: "gpu" is a word
              |
              c
              |
              l
              |
              o
              |
              u
              |
              d   <- terminal: "gpucloud" is a word
```

The flag is what distinguishes a stored word from a prefix of a longer word. Without
it, `"gp"` and `"gpu"` would be indistinguishable, and `search("gp")` would report
`true`.

## Implementation

```rust
//! Trie / prefix tree.
//!
//! Relevant to NVIDIA-style SDK/CLI/codegen work: autocomplete, filtering GPU
//! SKUs, command completion, and prefix matching.

use std::collections::HashMap;

#[derive(Default)]
pub struct Trie {
    root: Node,
}

#[derive(Default)]
struct Node {
    children: HashMap<char, Node>,
    terminal: bool,
}

impl Trie {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, word: &str) {
        let mut node = &mut self.root;
        for ch in word.chars() {
            node = node.children.entry(ch).or_default();
        }
        node.terminal = true;
    }

    pub fn search(&self, word: &str) -> bool {
        self.find_node(word).is_some_and(|node| node.terminal)
    }

    pub fn starts_with(&self, prefix: &str) -> bool {
        self.find_node(prefix).is_some()
    }

    fn find_node(&self, word: &str) -> Option<&Node> {
        let mut node = &self.root;
        for ch in word.chars() {
            node = node.children.get(&ch)?;
        }
        Some(node)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trie_insert_search_and_prefix() {
        let mut trie = Trie::new();
        trie.insert("gpu");
        trie.insert("gpucloud");

        assert!(trie.search("gpu"));
        assert!(trie.search("gpucloud"));
        assert!(!trie.search("gp"));
        assert!(!trie.search("gpucloudapi"));

        assert!(trie.starts_with("gp"));
        assert!(trie.starts_with("gpucloud"));
        assert!(!trie.starts_with("h100"));
    }
}
```

`insert` walks with `&mut` and creates children on demand:
`node.children.entry(ch).or_default()` inserts an empty node the first time the
character is seen and returns a mutable reference to the existing one otherwise. The
walk ends with a mutable reference to the final node, and one assignment sets the flag.

`find_node` is the read-only counterpart, and it uses `?` to leave the loop early:
`node.children.get(&ch)?` returns `None` from the function when the character is
absent. That one expression replaces a conditional and a `return`.

`is_some_and(|node| node.terminal)` combines two questions into one expression: does
the path exist, and is its end a word. Without the second part, `search` would answer
the same question as `starts_with`.

## Intuition

```text
insert("gpu")
  node = root
  'g' -> root.children has no 'g', so it is created; node = that node
  'p' -> created; node = that node
  'u' -> created; node = that node
  node.terminal = true

insert("gpucloud")
  'g', 'p', 'u' all exist, so the walk reuses the nodes built above
  'c', 'l', 'o', 'u', 'd' are created
  node.terminal = true

search("gp")        the walk succeeds, the final node's terminal flag is false
                    -> false
starts_with("gp")   the walk succeeds -> true
search("gpucloudapi")
                    'a' is absent after "gpucloud" -> the walk returns None
                    -> false
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `insert` | `O(k)` expected | one node per character not already present |
| `search` | `O(k)` expected | none |
| `starts_with` | `O(k)` expected | none |

`k` counts characters, because `word.chars()` iterates over Unicode scalar values.

## Limitations

**One node per distinct character position.** The structure stores a `HashMap` per
node, and a `HashMap` is larger than the characters it holds. A set of strings with no
shared prefixes occupies more memory than the same strings in a vector. A radix tree
compresses chains of single-child nodes and recovers most of that space; the file does
not implement one.

**There is no deletion.** Removing a word means clearing a terminal flag and then
pruning the nodes that are no longer on any path to a word. Neither operation is
present, so the only way to empty the structure is to drop it.

**There is no query that returns the words under a prefix.** `starts_with` answers a
boolean, and a caller that wants the completions must write its own traversal. The
structure supports the query; the API does not expose it.

**The node type is not public, and neither is the root.** A caller cannot inspect the
tree's shape, count its nodes, or measure its memory from outside the module. For a
teaching structure that is a defensible choice, and it means a memory question can only
be answered by reading the source.

## References

- Edward Fredkin, "Trie memory", *Communications of the ACM* 3(9), 1960, pages
  490–499.
- Donald E. Knuth, *The Art of Computer Programming*, Volume 3, 2nd edition,
  Addison-Wesley, 1998, Section 6.3, "Digital Searching".
- Standard library, [`HashMap::entry`](https://doc.rust-lang.org/std/collections/struct.HashMap.html#method.entry).
- Standard library, [`Option::is_some_and`](https://doc.rust-lang.org/std/option/enum.Option.html#method.is_some_and), stabilised in Rust 1.70.0.
