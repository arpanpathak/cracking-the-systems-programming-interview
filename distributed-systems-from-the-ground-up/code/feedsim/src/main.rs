//! Command feedsim counts the work of building a news feed in 2 ways: by
//! copying each post to the feed of every follower when it is written, and
//! by collecting the posts of everyone a reader follows when the feed is
//! read. It then counts a mixture of the 2.
//!
//! Run it from code/ with:
//!
//!     cargo run -p feedsim

// ANCHOR: accounts
/// An account: how many accounts follow it, how many it follows, and how
/// often per day it posts and reads its feed.
struct Account {
    followers: u64,
    follows: u64,
    posts: u64,
    reads: u64,
}

/// 1000 ordinary accounts and 1 account with 2 million followers.
fn accounts() -> Vec<Account> {
    let ordinary = || Account {
        followers: 200,
        follows: 200,
        posts: 2,
        reads: 20,
    };
    let mut all: Vec<Account> = std::iter::repeat_with(ordinary)
        .take(1000)
        .collect();

    all.push(Account {
        followers: 2_000_000,
        follows: 100,
        posts: 10,
        reads: 5,
    });

    all
}
// ANCHOR_END: accounts

// ANCHOR: cost
/// The copies made per day when every post is copied to every follower.
fn on_write(accounts: &[Account], limit: u64) -> u64 {
    accounts
        .iter()
        .filter(|account| account.followers <= limit)
        .map(|account| account.posts * account.followers)
        .sum()
}

/// The lists fetched per day when a reader collects the posts of each
/// account it follows that has more than `limit` followers.
fn on_read(accounts: &[Account], followed_large: u64) -> u64 {
    accounts
        .iter()
        .map(|account| account.reads * followed_large.min(account.follows))
        .sum()
}

fn main() {
    let accounts = accounts();
    let everyone = u64::MAX;

    println!(
        "copy on write for every account: {:>10} copies per day",
        on_write(&accounts, everyone)
    );
    println!(
        "collect on read for every account: {:>8} lists fetched per day",
        on_read(&accounts, 200)
    );

    let copies = on_write(&accounts, 10_000);
    let fetched = on_read(&accounts, 1);

    println!("mixture, copy unless the author has over 10000 followers:");
    println!("  {copies:>10} copies per day, {fetched:>8} lists fetched per day");
}
// ANCHOR_END: cost
