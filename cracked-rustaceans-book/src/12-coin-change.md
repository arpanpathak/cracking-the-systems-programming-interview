# 12. Coin Change {#coin-change}

*Source file: [`src/problems/dp.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/dp.rs). Test it with `cargo test dp`.*

> I call it my billion-dollar mistake. It was the invention of the null
> reference in 1965.
>
>, C. A. R. Hoare, QCon London, 2009

## Problem Statement

Given a list of coin denominations and a target amount, return the smallest number
of coins whose values sum exactly to the amount, or report that no combination
exists. Each denomination may be used any number of times.

## Designing a Solution

A greedy rule does not work. Taking the largest coin that fits fails for
`coins = [1, 3, 4]` and `amount = 6`: the greedy choice of `4` leaves `2`, which
needs two more coins, for a total of three, while `3 + 3` needs two.

The recurrence is over amounts. Let `dp[t]` be the smallest number of coins that
sums to `t`. The last coin used is some denomination `c`, and everything before it
must sum to `t - c` in the smallest possible number of coins:

```text
dp[0] = 0
dp[t] = min over c of ( dp[t - c] + 1 )     for each c <= t
```

Each entry depends only on entries at smaller amounts, so filling the table in
ascending order of `t` visits every dependency before it is needed.

```text
coins = [1, 2, 5],  amount = 11

t     :  0   1   2   3   4   5   6   7   8   9  10  11
dp    :  0   1   1   2   2   1   2   2   3   3   2   3

dp[11] was built from dp[11 - 5] + 1 = dp[6] + 1 = 2 + 1 = 3
and 11 = 5 + 5 + 1
```

## Implementation

```rust
//! Coin Change: minimum number of coins to make an amount.
//!
//! Classic dynamic programming. `Option<i32>` expresses "impossible" instead of
//! a magic `-1`.

pub fn coin_change(coins: &[i32], amount: i32) -> Option<i32> {
    if amount < 0 {
        return None;
    }

    let amount = amount as usize;
    let mut dp = vec![usize::MAX; amount + 1];
    dp[0] = 0;

    for total in 1..=amount {
        for &coin in coins {
            let coin = coin as usize;
            if coin > total || dp[total - coin] == usize::MAX {
                continue;
            }
            dp[total] = dp[total].min(dp[total - coin] + 1);
        }
    }

    match dp[amount] {
        usize::MAX => None,
        count => Some(count as i32),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn computes_minimum_coins() {
        assert_eq!(coin_change(&[1, 2, 5], 11), Some(3)); // 5 + 5 + 1
        assert_eq!(coin_change(&[2], 3), None);
        assert_eq!(coin_change(&[1], 0), Some(0));
    }
}
```

`usize::MAX` is the sentinel for "no combination reaches this amount yet". It is
safe as a marker because a real answer can never be that large: any combination
uses at most `amount` coins, because every coin is worth at least one.

The guard `if coin > total || dp[total - coin] == usize::MAX` does two things at
once. It skips a coin that is too large to be the last coin, and it skips a coin
whose remainder is itself unreachable. Without the second test the addition below
would add one to the sentinel and produce a wrong answer that looks reachable.

`dp[total] = dp[total].min(dp[total - coin] + 1)` keeps the best count found so
far for this amount. Because `dp[total]` is read and written in the same
statement, the loop order over coins does not matter.

The boundary conversion is where the sentinel stops. `match dp[amount]` translates
`usize::MAX` into `None` and everything else into `Some(count as i32)`, so no
caller ever sees the marker. The type of the answer is `Option<i32>`, which is the
part of the design that matters: "impossible" is not a number.

## Intuition

```text
coins = [1, 2, 5], amount = 11

total = 1   coin 1: dp[1] = min(MAX, dp[0] + 1) = 1
total = 2   coin 1: dp[2] = min(MAX, dp[1] + 1) = 2
            coin 2: dp[2] = min(2, dp[0] + 1)   = 1
total = 3   coin 1: dp[3] = min(MAX, dp[2] + 1) = 2
            coin 2: dp[3] = min(2, dp[1] + 1)   = 2
total = 4   coin 1: dp[4] = min(MAX, dp[3] + 1) = 3
            coin 2: dp[4] = min(3, dp[2] + 1)   = 2
total = 5   coin 1: dp[5] = min(MAX, dp[4] + 1) = 3
            coin 2: dp[5] = min(3, dp[3] + 1)   = 3
            coin 5: dp[5] = min(3, dp[0] + 1)   = 1
...
total = 11  coin 1: dp[11] = min(MAX, dp[10] + 1) = 3
            coin 2: dp[11] = min(3, dp[9] + 1)    = 3
            coin 5: dp[11] = min(3, dp[6] + 1)    = 3
```

```text
coins = [2], amount = 3

total = 1   coin 2 is larger than total, skipped;   dp[1] = MAX
total = 2   coin 2: dp[0] = 0, so dp[2] = 1
total = 3   coin 2: dp[1] = MAX, skipped;           dp[3] = MAX

dp[3] is the sentinel, so the result is None.
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(amount × coins.len())` | every amount considers every denomination |
| Space | `O(amount)` | one machine word per amount |

## Limitations

**The table is allocated from the amount alone.** `coin_change(&[1], i32::MAX)`
asks for a vector of `i32::MAX + 1` machine words, which is sixteen gigabytes on a
64-bit target. The allocation failure aborts the process, because the standard
library's allocation error handling calls `handle_alloc_error`, which aborts. A
version that accepts an amount from the network would validate it against a limit
first, or use `Vec::try_reserve` to turn the failure into a `Result`.

**A negative coin is treated as a very large positive one.** `coin as usize`
converts `-1` to `usize::MAX`, and the guard `coin > total` then skips it on every
iteration. The function returns an answer that ignores the negative coin, which is
the wrong answer if the caller meant the coin to be usable. Nothing reports the
conversion.

**A zero coin is skipped by the same guard, correctly.** `coin = 0` passes the
first test only when `total` is zero, and the loop starts at one, so a zero
denomination contributes nothing. That is the right behaviour and it is a
consequence of the guard rather than a stated rule.

**The function returns the count, not the coins.** A caller that wants to know
which coins to use needs the predecessor that produced each entry, which means a
second table recording decisions. The current one-minimum-per-entry design cannot
reconstruct the combination.

**`i32` bounds both the amount and the answer.** An amount above `i32::MAX` cannot
be passed, and the conversion `count as i32` is safe only because the answer is at
most the amount.

## Summary

- The recurrence decides on the last coin: `dp[total]` is one more than the best
  `dp[total - coin]`, which is what makes the table a dynamic program rather than a
  sequence of locally optimal choices.
- A greedy choice is not correct here. For `[1, 3, 4]` and the amount `6`, greedy
  produces `4 + 1 + 1` and the optimum is `3 + 3`.
- The table holds `usize::MAX` as a sentinel for an unreachable amount, and the
  boundary converts it to `None`, so a caller never sees the sentinel. The
  conversion `count as i32` is safe because the answer is at most the amount.
- The allocation is controlled by the input. `coin_change(&[1], i32::MAX)` requests
  a vector of `i32::MAX + 1` machine words, and a failed allocation aborts the
  process.
- The function returns the count and not the coins. Reconstructing the combination
  needs the predecessor that produced each entry, which is a second table.

## References

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Chapter 14, "Dynamic
  Programming".
- Richard Bellman, *Dynamic Programming*, Princeton University Press, 1957.
- Standard library, [`usize::MAX`](https://doc.rust-lang.org/std/primitive.usize.html#associatedconstant.MAX).
- Standard library, [`Vec::try_reserve`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.try_reserve).
