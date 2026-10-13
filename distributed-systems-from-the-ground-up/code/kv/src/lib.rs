//! A key-value store for one node that keeps every acknowledged write across
//! a crash. A write is appended to a log on disk before it is applied in
//! memory, and the log is read back when the store is opened.

pub mod log;
pub mod record;
pub mod store;

pub use log::{Log, Recovery};
pub use record::{Change, Decoded, Record};
pub use store::{Condition, Entry, Store, StoreError, Summary, Write, Written, apply, check, page};
