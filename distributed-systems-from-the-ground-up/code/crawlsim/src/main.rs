//! Command crawlsim crawls a small made-up web. It keeps 1 queue for every
//! host, waits between 2 requests to the same host, fetches no address
//! twice, and stops following a host that produces pages without end.
//!
//! Run it from code/ with:
//!
//!     cargo run -p crawlsim

// ANCHOR: imports
use std::collections::{BTreeMap, BTreeSet, VecDeque};
// ANCHOR_END: imports

// ANCHOR: web
/// The seconds a crawler waits between 2 requests to the same host.
const POLITENESS: u64 = 2;

/// The largest number of pages the crawler takes from 1 host.
const BUDGET: usize = 4;

/// The links found on a page. The host `calendar` links every page to the
/// next day, without end.
fn links(address: &str) -> Vec<String> {
    let fixed: &[&str] = match address {
        "news/" => &["news/a", "news/b", "shop/", "calendar/day-1"],
        "news/a" => &["news/", "news/b"],
        "news/b" => &["news/a", "shop/item-1"],
        "shop/" => &["shop/item-1", "shop/item-2", "news/"],
        "shop/item-1" | "shop/item-2" => &["shop/"],
        _other => &[],
    };
    let next_day = address
        .strip_prefix("calendar/day-")
        .and_then(|day| day.parse::<u32>().ok())
        .map(|day| format!("calendar/day-{}", day + 1));

    fixed
        .iter()
        .map(|link| (*link).to_owned())
        .chain(next_day)
        .collect()
}

fn host(address: &str) -> &str {
    address
        .split_once('/')
        .map_or(address, |parts| parts.0)
}
// ANCHOR_END: web

// ANCHOR: frontier
/// The addresses still to be fetched, in 1 queue for every host, with the
/// time at which each host may next be asked.
#[derive(Default)]
struct Frontier {
    queues: BTreeMap<String, VecDeque<String>>,
    ready_at: BTreeMap<String, u64>,
    seen: BTreeSet<String>,
    taken: BTreeMap<String, usize>,
    skipped: usize,
    over_budget: usize,
}

impl Frontier {
    /// Adds an address, unless it was added before or its host has given
    /// its share of pages.
    fn add(&mut self, address: String) {
        let host = host(&address).to_owned();
        let taken = self
            .taken
            .entry(host.clone())
            .or_default();

        if !self.seen.insert(address.clone()) {
            self.skipped += 1;

            return;
        }

        if *taken == BUDGET {
            self.over_budget += 1;

            return;
        }

        *taken += 1;
        self.queues
            .entry(host)
            .or_default()
            .push_back(address);
    }

    /// The next address of every host that may be asked at time `now`.
    fn take(&mut self, now: u64) -> Vec<String> {
        let ready: Vec<String> = self
            .queues
            .keys()
            .filter(|host| {
                self.ready_at
                    .get(*host)
                    .is_none_or(|&at| at <= now)
            })
            .cloned()
            .collect();

        ready
            .into_iter()
            .filter_map(|host| {
                let address = self
                    .queues
                    .get_mut(&host)?
                    .pop_front()?;

                self.ready_at
                    .insert(host, now + POLITENESS);

                Some(address)
            })
            .collect()
    }

    fn is_empty(&self) -> bool {
        self.queues
            .values()
            .all(VecDeque::is_empty)
    }
}
// ANCHOR_END: frontier

// ANCHOR: main
fn main() {
    let mut frontier = Frontier::default();
    let mut fetched = 0;

    frontier.add("news/".to_owned());

    for now in 0.. {
        if frontier.is_empty() {
            break;
        }

        let batch = frontier.take(now);

        if !batch.is_empty() {
            println!("t={now:2}  fetch {}", batch.join(", "));
        }

        fetched += batch.len();
        batch
            .iter()
            .flat_map(|address| links(address))
            .for_each(|link| frontier.add(link));
    }

    println!("pages fetched: {fetched}");
    println!("links to addresses already seen: {}", frontier.skipped);
    println!(
        "links not followed because a host had given {BUDGET} pages: {}",
        frontier.over_budget
    );
}
// ANCHOR_END: main
