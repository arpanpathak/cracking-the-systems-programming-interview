use std::mem;

fn min_distance(word1: &str, word2: &str) -> i32 {
    let (word1, word2) = (word1.as_bytes(), word2.as_bytes());
    let (m, n) = (word1.len(), word2.len());

    // dp[i][j] = fewest edits to turn the first i letters of word1
    //            into the first j letters of word2.
    //
    // Why only look at the last letters?
    // In the best edit sequence, word2's last letter came from somewhere,
    // and word1's last letter went somewhere. There are only 3 possibilities:
    //   - word1's last letter got deleted
    //   - word2's last letter got inserted
    //   - word1's last letter turned into word2's last letter (free if equal, else 1 swap)
    // We don't know which one the best answer used, so try all 3 and take the min.
    //
    // Each row only needs the row above it, so keep just two rows:
    //   prev[x] = dp[i-1][x], curr[x] = dp[i][x].
    let mut prev = vec![0; n + 1];
    let mut curr = vec![0; n + 1];

    for i in 0..=m {
        for j in 0..=n {
            curr[j] = match (i, j) {
                // word1 is empty, word2 has j letters.
                // Nothing to reuse, so every letter must be inserted.
                (0, _) => j,

                // word2 is empty, word1 has i letters.
                // Every letter is unwanted, so every letter must be deleted.
                (_, 0) => i,

                // Last letters are equal, so pair them up for free.
                // Both words lose their last letter, and the rest is
                // word1's first i-1 vs word2's first j-1 = dp[i-1][j-1].
                _ if word1[i - 1] == word2[j - 1] => prev[j - 1],

                _ => {
                    // Delete word1's last letter.
                    // word1 shrinks to i-1 letters, but word2 still needs all j
                    // (we haven't produced any of word2 yet) -> dp[i-1][j].
                    let delete = prev[j];

                    // Insert word2's last letter at the end of word1.
                    // That covers word2's last letter, so word2 shrinks to j-1.
                    // But word1 still has all i of its own letters to deal with -> dp[i][j-1].
                    let insert = curr[j - 1];

                    // Change word1's last letter into word2's last letter.
                    // Now they're equal, like the match case, so both shrink -> dp[i-1][j-1].
                    let replace = prev[j - 1];

                    // +1 for the delete/insert/change we just did.
                    1 + delete.min(insert).min(replace)
                }
            };
        }

        // This row becomes the "row above" for the next one.
        mem::swap(&mut prev, &mut curr);
    }

    // After the last swap, the final row is in prev.
    prev[n] as i32
}

fn main() {
    println!("{}", min_distance("horse", "ros"));           // 3
    println!("{}", min_distance("intention", "execution")); // 5
}
