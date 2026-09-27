//! The client's local copy of the server's objects.

use crate::server::{Event, EventType, Object};
use std::collections::HashMap;
use std::sync::RwLock;

/// The client's copy of the server's objects, kept current by a
/// [`Reflector`](crate::reflector::Reflector). Its methods are safe to call
/// from several threads.
#[derive(Default)]
pub struct Cache {
    /// The latest known state of every object, keyed by name.
    objects: RwLock<HashMap<String, Object>>,
}

impl Cache {
    /// Returns the cached copy of the named object, if it exists.
    pub fn get(&self, name: &str) -> Option<Object> {
        let objects = self.objects.read().expect("cache lock poisoned");
        objects.get(name).cloned()
    }

    /// Records one event from a watch.
    pub fn apply(&self, event: Event) {
        let mut objects = self.objects.write().expect("cache lock poisoned");
        match event.kind {
            EventType::Deleted => objects.remove(&event.object.name),
            EventType::Added | EventType::Modified => {
                objects.insert(event.object.name.clone(), event.object)
            }
        };
    }

    /// Installs the result of a fresh list and returns the names of the
    /// objects that changed, including objects that disappeared while the
    /// client was not watching.
    pub fn replace(&self, list: &[Object]) -> Vec<String> {
        let mut objects = self.objects.write().expect("cache lock poisoned");
        let old = std::mem::take(&mut *objects);
        let mut changed = Vec::new();
        for object in list {
            let old_version = old.get(&object.name).map(|o| o.resource_version);
            if old_version != Some(object.resource_version) {
                changed.push(object.name.clone());
            }
            objects.insert(object.name.clone(), object.clone());
        }
        for name in old.keys() {
            if !objects.contains_key(name) {
                changed.push(name.clone());
            }
        }
        changed
    }
}
