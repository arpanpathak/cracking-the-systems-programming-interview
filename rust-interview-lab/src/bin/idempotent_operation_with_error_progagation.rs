use std::collections::HashMap;
use std::hash::Hash;
use std::sync::Mutex;

type RuntimeError = Box<dyn std::error::Error>;

pub struct Idempotent<K, V> {
    store: Mutex<HashMap<K, V>>,
}

impl<K, V> Idempotent<K, V>
where
    K: Eq + Hash + Clone,
    V: Clone,
{
    pub fn new() -> Self {
        Self { store: Mutex::new(HashMap::new()) }
    }

    pub fn execute<F>(&self, key: K, f: F) -> Result<V, RuntimeError>
    where
        F: FnOnce() -> Result<V, RuntimeError>,
    {
        let mut store = self.store.lock().map_err(|_| "lock poisoned")?;
        if let Some(v) = store.get(&key) {
            return Ok(v.clone());
        }
        let v = f()?;
        store.insert(key, v.clone());
        Ok(v)
    }
}

fn main() -> Result<(), RuntimeError> {
    let idem = Idempotent::new();

    let charge = || -> Result<String, RuntimeError> {
        println!("charging card...");
        Ok("txn_42".into())
    };

    assert_eq!(idem.execute("order-1", charge)?, "txn_42");
    assert_eq!(idem.execute("order-1", charge)?, "txn_42");
    Ok(())
}
