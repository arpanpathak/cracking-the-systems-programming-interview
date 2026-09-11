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
