/// dp[i][j] = min edits to turn the first i chars of word1
///            into the first j chars of word2.
///
/// Every cell looks at the last char of each prefix, word1[i-1] and word2[j-1],
/// and asks: what was the last edit?
///
///   dp[i-1][j]   + 1  DELETE word1[i-1]. Throw away word1's last char; what's left,
///                     word1[..i-1], still has to become all of word2[..j].
///   dp[i][j-1]   + 1  INSERT word2[j-1]. Append word2's last char to the end, which
///                     settles it; word1[..i] now only has to become word2[..j-1].
///   dp[i-1][j-1] + 1  REPLACE word1[i-1] with word2[j-1]. Both last chars are now
///                     settled, so both prefixes shrink by one.
///   dp[i-1][j-1]      MATCH. Last chars are already equal: keep them for free.
fn min_distance(word1: &str, word2: &str) -> i32 {
    let (word1, word2) = (word1.as_bytes(), word2.as_bytes());
    let (m, n) = (word1.len(), word2.len());

    let mut dp = vec![vec![0; n + 1]; m + 1];

    for i in 0..=m {
        for j in 0..=n {
            dp[i][j] = match (i, j) {
                // word1 prefix is empty: the only way to build word2[..j] is to insert all j chars.
                (0, _) => j,
                // word2 prefix is empty: the only way to reach it is to delete all i chars of word1.
                (_, 0) => i,
                // last chars match: no edit needed, solve the rest.
                _ if word1[i - 1] == word2[j - 1] => dp[i - 1][j - 1],
                // last chars differ: pay 1 for the cheapest of the three edits.
                _ => 1 + dp[i - 1][j]       // delete
                    .min(dp[i][j - 1])      // insert
                    .min(dp[i - 1][j - 1]), // replace
            };
        }
    }

    dp[m][n] as i32
}

// Space optimized version
use std::mem;

fn min_distance_constant_space(word1: &str, word2: &str) -> i32 {
    let (word1, word2) = (word1.as_bytes(), word2.as_bytes());
    let (m, n) = (word1.len(), word2.len());

    // dp[i][j] = min edits to turn word1[..i] into word2[..j].
    // Row i only reads row i-1, so two rows are enough:
    //   prev = row i-1, curr = row i.
    let mut prev = vec![0; n + 1];
    let mut curr = vec![0; n + 1];

    for i in 0..=m {
        for j in 0..=n {
            curr[j] = match (i, j) {
                // word1[..0] is empty: the only way to build word2[..j]
                // is to insert all j chars.
                (0, _) => j,

                // word2[..0] is empty: the only way to get there
                // is to delete all i chars of word1.
                (_, 0) => i,

                // Last chars already match: keep them for free,
                // what's left is turning word1[..i-1] into word2[..j-1].
                _ if word1[i - 1] == word2[j - 1] => prev[j - 1],

                // Last chars differ: pay 1 for whichever edit is cheapest.
                _ => {
                    // DELETE word1[i-1]: drop word1's last char, the remaining
                    // word1[..i-1] still has to become all of word2[..j].
                    let delete = prev[j];

                    // INSERT word2[j-1]: append word2's last char, which settles it,
                    // so word1[..i] only has to become word2[..j-1].
                    let insert = curr[j - 1];

                    // REPLACE word1[i-1] with word2[j-1]: both last chars settled,
                    // so both prefixes shrink by one.
                    let replace = prev[j - 1];

                    1 + delete.min(insert).min(replace)
                }
            };
        }

        // Row i becomes the "previous" row for i+1.
        mem::swap(&mut prev, &mut curr);
    }

    // After the final swap, the last computed row sits in prev.
    prev[n] as i32
}

fn main() {
    println!("{}", min_distance("horse", "ros"));           // 3
    println!("{}", min_distance("intention", "execution")); // 5
}
