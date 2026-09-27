//! Reconciles objects whose names arrive on the work queue.

use crate::cache::Cache;
use crate::log;
use crate::queue::WorkQueue;
use crate::server::{ApiError, ApiServer};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

/// Makes each object's status agree with its spec.
pub struct Controller {
    /// Receives the controller's status writes.
    pub server: Arc<ApiServer>,
    /// Supplies the current state of each object.
    pub cache: Arc<Cache>,
    /// Supplies the names of objects to reconcile.
    pub queue: Arc<WorkQueue>,
}

impl Controller {
    /// A single worker: takes names from the queue one at a time and
    /// reconciles them. It does not return.
    pub fn run(&self) {
        loop {
            let name = self.queue.get();
            let result = self.reconcile(&name);
            self.queue.done(&name);
            if result.is_err() {
                self.queue.add([name]); // client-go requeues with a backoff
            }
        }
    }

    /// Reads the named object from the cache and, if its status differs from
    /// its spec, writes a new status conditioned on the version it read.
    fn reconcile(&self, name: &str) -> Result<(), ApiError> {
        let Some(mut object) = self.cache.get(name) else {
            log!("reconcile {name}: deleted, releasing its GPUs");
            return Ok(());
        };
        if object.status.gpus == object.spec.gpus {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(20)); // slow work, such as starting containers
        object.status.gpus = object.spec.gpus;
        let version = object.resource_version;
        match self.server.update(object.clone()) {
            Ok(()) => {
                log!("reconcile {name}: status.gpus = {}", object.status.gpus);
                Ok(())
            }
            Err(error) => {
                log!("reconcile {name}: write at version {version}: {error}");
                Err(error)
            }
        }
    }
}
