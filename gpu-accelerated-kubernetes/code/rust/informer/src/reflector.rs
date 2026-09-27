//! Keeps a [`Cache`] current by listing and watching the server.

use crate::cache::Cache;
use crate::log;
use crate::queue::WorkQueue;
use crate::server::{ApiError, ApiServer};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

/// Copies the server's objects into a cache and queues the name of every
/// object that changes.
pub struct Reflector {
    /// The source of objects and events.
    pub server: Arc<ApiServer>,
    /// Receives every object the reflector sees.
    pub cache: Arc<Cache>,
    /// Receives the name of every object that changes.
    pub queue: Arc<WorkQueue>,
}

impl Reflector {
    /// Lists every object, watches from the list's version, and lists again
    /// whenever the server can no longer resume the watch. It does not return.
    pub fn run(&self) {
        loop {
            let (list, version) = self.server.list();
            self.queue.add(self.cache.replace(&list));
            let objects: Vec<String> = list.iter().map(ToString::to_string).collect();
            log!(
                "reflector: list at version {version}: [{}]",
                objects.join(" ")
            );
            self.watch_from(version);
        }
    }

    /// Applies events from `version` onward, reopens the watch after each
    /// disconnect, and returns when the server reports that the history is gone.
    fn watch_from(&self, mut version: u64) {
        loop {
            let events = match self.server.watch(version) {
                Ok(events) => events,
                Err(ApiError::Gone) => {
                    log!(
                        "reflector: watch from version {version}: {}",
                        ApiError::Gone
                    );
                    return;
                }
                Err(_) => {
                    thread::sleep(Duration::from_millis(10)); // client-go backs off exponentially
                    continue;
                }
            };
            for event in events {
                version = event.object.resource_version;
                let name = event.object.name.clone();
                // Update the cache before queueing the name, so that a worker
                // that takes the name reads the object as of this event.
                self.cache.apply(event);
                self.queue.add([name]);
            }
            log!("reflector: watch closed, resuming from version {version}");
        }
    }
}
