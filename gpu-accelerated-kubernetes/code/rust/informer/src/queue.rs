//! The work queue between the reflector and the controller.

use std::collections::{HashSet, VecDeque};
use std::sync::{Condvar, Mutex, MutexGuard};

/// The queue's data, kept behind one lock.
#[derive(Default)]
struct State {
    /// The names ready for a worker, in arrival order.
    ready: VecDeque<String>,
    /// Every name that needs processing.
    dirty: HashSet<String>,
    /// Every name that a worker currently holds.
    processing: HashSet<String>,
}

/// Stores the names of objects that need reconciling. A name waits in the
/// queue at most once, and a name that a worker holds is handed to no other
/// worker until the first calls [`WorkQueue::done`].
#[derive(Default)]
pub struct WorkQueue {
    /// Guards the queue's data.
    state: Mutex<State>,
    /// Wakes workers blocked in [`WorkQueue::get`].
    ready: Condvar,
}

impl WorkQueue {
    /// Locks the queue's data.
    fn state(&self) -> MutexGuard<'_, State> {
        self.state.lock().expect("queue lock poisoned")
    }

    /// Marks each name as needing processing. A name that is already pending
    /// is left where it is. A name that a worker holds is queued again by `done`.
    pub fn add(&self, names: impl IntoIterator<Item = String>) {
        let mut state = self.state();
        for name in names {
            if !state.dirty.insert(name.clone()) {
                continue;
            }
            if !state.processing.contains(&name) {
                state.ready.push_back(name);
                self.ready.notify_one();
            }
        }
    }

    /// Blocks until a name is ready and hands it to the caller.
    pub fn get(&self) -> String {
        let mut state = self.state();
        loop {
            if let Some(name) = state.ready.pop_front() {
                state.dirty.remove(&name);
                state.processing.insert(name.clone());
                return name;
            }
            state = self.ready.wait(state).expect("queue lock poisoned");
        }
    }

    /// Releases a name that `get` handed out, and queues it again if it was
    /// added while the worker held it.
    pub fn done(&self, name: &str) {
        let mut state = self.state();
        state.processing.remove(name);
        if state.dirty.contains(name) {
            state.ready.push_back(name.to_string());
            self.ready.notify_one();
        }
    }
}
