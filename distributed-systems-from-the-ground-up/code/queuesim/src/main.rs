//! Command queuesim runs a small message queue: a topic of 2 partitions, a
//! producer, and a consumer that crashes after it has processed messages
//! and before it has said so. It shows that messages are delivered again,
//! and how the consumer avoids acting on them twice.
//!
//! Run it from code/ with:
//!
//!     cargo run -p queuesim

// ANCHOR: imports
use std::collections::HashSet;

use xxhash_rust::xxh3::xxh3_64;
// ANCHOR_END: imports

// ANCHOR: topic
/// A message: the key that chooses its partition, and its contents.
#[derive(Clone)]
struct Message {
    key: String,
    body: String,
}

/// A topic: several partitions, each a log that only grows.
struct Topic {
    partitions: Vec<Vec<Message>>,
}

impl Topic {
    fn new(partitions: usize) -> Topic {
        Topic {
            partitions: vec![Vec::new(); partitions],
        }
    }

    /// Appends a message to the partition of its key and returns the
    /// partition and the offset. Messages with one key keep their order.
    fn produce(&mut self, key: &str, body: &str) -> (usize, usize) {
        let partition = (xxh3_64(key.as_bytes()) % self.partitions.len() as u64) as usize;
        let log = &mut self.partitions[partition];

        log.push(Message {
            key: key.to_owned(),
            body: body.to_owned(),
        });

        (partition, log.len() - 1)
    }
}
// ANCHOR_END: topic

// ANCHOR: consumer
/// A consumer of one partition. The queue remembers `committed`, the
/// offset up to which the consumer has confirmed its work.
struct Consumer {
    committed: usize,
    /// The messages this consumer has acted on, by partition and offset.
    done: HashSet<(usize, usize)>,
    actions: usize,
}

impl Consumer {
    /// Reads from the committed offset and acts on each message that it has
    /// not acted on before. With `commit`, it then confirms the new offset.
    fn poll(&mut self, topic: &Topic, partition: usize, commit: bool) {
        let log = &topic.partitions[partition];

        for (offset, message) in log
            .iter()
            .enumerate()
            .skip(self.committed)
        {
            let first_time = self
                .done
                .insert((partition, offset));

            let verdict = match first_time {
                true => "acted on",
                false => "seen before, skipped",
            };

            self.actions += usize::from(first_time);
            println!(
                "  offset {offset}: {} {} -> {verdict}",
                message.key, message.body
            );
        }

        if commit {
            self.committed = log.len();
        }
    }
}
// ANCHOR_END: consumer

// ANCHOR: main
fn main() {
    let mut topic = Topic::new(2);

    for (key, body) in [
        ("order-7", "created"),
        ("order-8", "created"),
        ("order-7", "paid"),
        ("order-9", "created"),
        ("order-7", "shipped"),
    ] {
        let (partition, offset) = topic.produce(key, body);

        println!("produced {key} {body}: partition {partition}, offset {offset}");
    }

    let partition = topic
        .produce("order-7", "delivered")
        .0;
    let mut consumer = Consumer {
        committed: 0,
        done: HashSet::new(),
        actions: 0,
    };

    println!("the consumer reads partition {partition} and crashes before it commits");
    consumer.poll(&topic, partition, false);

    println!("it restarts and reads from the committed offset, which is still 0");
    consumer.poll(&topic, partition, true);

    println!(
        "messages in the partition: {}, actions taken: {}, committed offset: {}",
        topic.partitions[partition].len(),
        consumer.actions,
        consumer.committed
    );
}
// ANCHOR_END: main
