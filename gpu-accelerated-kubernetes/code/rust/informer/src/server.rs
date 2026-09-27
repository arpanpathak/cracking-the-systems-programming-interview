//! A model of the Kubernetes API server. It stores objects, numbers every
//! write, keeps a history of recent changes, and serves lists and watches.

use std::collections::HashMap;
use std::fmt;
use std::sync::Mutex;
use std::sync::mpsc::{Receiver, Sender, channel};

/// The part of an object that a user writes: the desired state.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Spec {
    /// Number of GPUs the job asks for.
    pub gpus: u32,
}

/// The part of an object that the controller writes: the observed state.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Status {
    /// Number of GPUs the controller has provided to the job.
    pub gpus: u32,
}

/// One stored record, such as a training job.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Object {
    /// Identifies the object on the server.
    pub name: String,
    /// What the user asked for.
    pub spec: Spec,
    /// What the controller has done about it.
    pub status: Status,
    /// The server's write counter at the object's latest change.
    pub resource_version: u64,
}

impl Object {
    /// Returns a new object with the given name and GPU request, an empty
    /// status, and no resource version.
    pub fn new(name: &str, gpus: u32) -> Self {
        Self {
            name: name.to_string(),
            spec: Spec { gpus },
            ..Self::default()
        }
    }
}

impl fmt::Display for Object {
    /// Formats an object for the demonstration's log lines.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}{{spec.gpus: {}, status.gpus: {}, v{}}}",
            self.name, self.spec.gpus, self.status.gpus, self.resource_version
        )
    }
}

/// The kind of change that an [`Event`] records.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EventType {
    /// The object was created.
    Added,
    /// The object was updated.
    Modified,
    /// The object was removed.
    Deleted,
}

/// One change to one object.
#[derive(Clone, Debug)]
pub struct Event {
    /// The kind of change.
    pub kind: EventType,
    /// The object after the change, or its final state if it was deleted.
    pub object: Object,
}

/// Errors that the server returns. The first two carry the HTTP status codes
/// that the Kubernetes API server uses for the same conditions.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ApiError {
    /// The history that a watch needs has been discarded.
    Gone,
    /// A conditional write carried an out-of-date resource version.
    Conflict,
    /// The client cannot reach the server.
    Unreachable,
}

impl fmt::Display for ApiError {
    /// Formats the error the way the Kubernetes API server reports it.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::Gone => "410 Gone: resource version too old",
            Self::Conflict => "409 Conflict: object has been modified",
            Self::Unreachable => "server unreachable",
        })
    }
}

/// Everything the server stores, kept behind one lock.
#[derive(Default)]
struct State {
    /// The last resource version the server handed out.
    version: u64,
    /// The current state of every object, keyed by name.
    objects: HashMap<String, Object>,
    /// The events newer than `compacted`, oldest first.
    history: Vec<Event>,
    /// The oldest version from which a watch may resume.
    compacted: u64,
    /// One sender for each open watch.
    watches: Vec<Sender<Event>>,
    /// Makes new watches fail, to simulate a network partition.
    unreachable: bool,
}

impl State {
    /// Appends `event` to the history and sends it to every open watch.
    /// Watches whose receiver has gone away are forgotten.
    fn publish(&mut self, event: Event) {
        self.watches.retain(|w| w.send(event.clone()).is_ok());
        self.history.push(event);
    }
}

/// Stores objects and streams their changes to watchers. Its methods are safe
/// to call from several threads.
#[derive(Default)]
pub struct ApiServer {
    /// Guards all of the server's data.
    state: Mutex<State>,
}

impl ApiServer {
    /// Locks the server's data.
    fn state(&self) -> std::sync::MutexGuard<'_, State> {
        self.state.lock().expect("server lock poisoned")
    }

    /// Creates or replaces an object. A non-zero `resource_version` is a
    /// condition: the caller read the object at that version and wants the
    /// write applied only if the object is still at it. Zero writes
    /// unconditionally.
    pub fn update(&self, mut object: Object) -> Result<(), ApiError> {
        let mut state = self.state();
        let current = state.objects.get(&object.name);
        let current_version = current.map_or(0, |o| o.resource_version);
        if object.resource_version != 0 && object.resource_version != current_version {
            return Err(ApiError::Conflict);
        }
        let kind = if current.is_some() {
            EventType::Modified
        } else {
            EventType::Added
        };
        state.version += 1;
        object.resource_version = state.version;
        state.objects.insert(object.name.clone(), object.clone());
        state.publish(Event { kind, object });
        Ok(())
    }

    /// Removes the named object, if it exists.
    pub fn delete(&self, name: &str) {
        let mut state = self.state();
        let Some(mut object) = state.objects.remove(name) else {
            return;
        };
        state.version += 1;
        object.resource_version = state.version;
        state.publish(Event {
            kind: EventType::Deleted,
            object,
        });
    }

    /// Returns every object, sorted by name, and the version at which the
    /// snapshot was taken.
    pub fn list(&self) -> (Vec<Object>, u64) {
        let state = self.state();
        let mut objects: Vec<Object> = state.objects.values().cloned().collect();
        objects.sort_by(|a, b| a.name.cmp(&b.name));
        (objects, state.version)
    }

    /// Returns a receiver that first delivers the stored events newer than
    /// `version` and then every new event, until the server drops the watch.
    pub fn watch(&self, version: u64) -> Result<Receiver<Event>, ApiError> {
        let mut state = self.state();
        if state.unreachable {
            return Err(ApiError::Unreachable);
        }
        if version < state.compacted {
            return Err(ApiError::Gone);
        }
        let (sender, receiver) = channel();
        for event in &state.history {
            if event.object.resource_version > version {
                sender.send(event.clone()).expect("receiver is held here");
            }
        }
        state.watches.push(sender);
        Ok(receiver)
    }

    /// Discards the event history, as etcd discards old versions.
    pub fn compact(&self) {
        let mut state = self.state();
        state.compacted = state.version;
        state.history.clear();
    }

    /// Closes every open watch, as a load balancer's idle timeout would.
    pub fn drop_watches(&self) {
        self.state().watches.clear();
    }

    /// Closes every open watch and makes new watches fail until [`Self::heal`].
    pub fn partition(&self) {
        let mut state = self.state();
        state.unreachable = true;
        state.watches.clear();
    }

    /// Ends a partition, so new watches succeed again.
    pub fn heal(&self) {
        self.state().unreachable = false;
    }
}
