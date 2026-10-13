//! Models epoll: an interest list of registered pipes, a ready list that a
//! write fills, and a wait that examines only the ready list. It repeats the
//! measurements of epollfacts on the model and then runs a small event loop
//! on it.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p eventloop
//! ```

// ANCHOR: types
/// The read end of a pipe as epoll sees it: the bytes waiting to be read, and
/// its registration. `queued` is set while the pipe is on the ready list.
#[derive(Clone, Default)]
struct Pipe {
    buffered: usize,
    registered: bool,
    edge: bool,
    queued: bool,
}

/// Holds the pipes and one epoll instance. The registered pipes are the
/// interest list. `ready` is the ready list, in the order in which the pipes
/// became ready. `examined` counts the registrations that waits and scans
/// have looked at.
struct Kernel {
    pipes: Vec<Pipe>,
    ready: Vec<usize>,
    examined: usize,
}

impl Kernel {
    fn new(pipes: usize) -> Kernel {
        Kernel {
            pipes: vec![Pipe::default(); pipes],
            ready: Vec::new(),
            examined: 0,
        }
    }
}
// ANCHOR_END: types

// ANCHOR: wake
impl Kernel {
    /// Adds a pipe to the interest list. A pipe that is already readable goes
    /// on the ready list at once.
    fn register(&mut self, index: usize, edge: bool) {
        let pipe = &mut self.pipes[index];

        pipe.registered = true;
        pipe.edge = edge;

        if pipe.buffered > 0 {
            self.enqueue(index);
        }
    }

    /// Puts a pipe on the ready list unless it is already there.
    fn enqueue(&mut self, index: usize) {
        if !self.pipes[index].queued {
            self.pipes[index].queued = true;
            self.ready.push(index);
        }
    }

    /// Adds bytes to a pipe. This is the moment the pipe becomes ready, and
    /// the writer puts it on the ready list.
    fn write(&mut self, index: usize, n: usize) {
        self.pipes[index].buffered += n;

        if self.pipes[index].registered {
            self.enqueue(index);
        }
    }

    /// Removes up to `n` bytes from a pipe and returns the number removed.
    fn read(&mut self, index: usize, n: usize) -> usize {
        let n = n.min(self.pipes[index].buffered);
        self.pipes[index].buffered -= n;

        n
    }
}
// ANCHOR_END: wake

// ANCHOR: wait
impl Kernel {
    /// Empties the ready list and returns the pipes on it that are still
    /// readable. A level-triggered pipe that is reported goes back on the
    /// list, so the next wait checks it again. An edge-triggered pipe does
    /// not, and is reported again only after another write.
    fn wait(&mut self) -> Vec<usize> {
        let queued = std::mem::take(&mut self.ready);
        let mut events = Vec::new();

        for index in queued {
            self.pipes[index].queued = false;
            self.examined += 1;

            if self.pipes[index].buffered == 0 {
                continue;
            }

            events.push(index);

            if !self.pipes[index].edge {
                self.enqueue(index);
            }
        }

        events
    }

    /// The method of select and poll: it examines every registered pipe on
    /// every call.
    fn scan(&mut self) -> Vec<usize> {
        let mut events = Vec::new();

        for (index, pipe) in self.pipes.iter().enumerate() {
            if !pipe.registered {
                continue;
            }

            self.examined += 1;

            if pipe.buffered > 0 {
                events.push(index);
            }
        }

        events
    }
}
// ANCHOR_END: wait

// ANCHOR: measure
/// Repeats the level-triggered measurement of epollfacts.
fn level() {
    let mut kernel = Kernel::new(3);

    for index in 0..3 {
        kernel.register(index, false);
    }

    println!(
        "3 pipes registered, none written: {} event(s)",
        kernel.wait().len()
    );

    kernel.write(1, 5);

    if let [index] = kernel.wait().as_slice() {
        println!("write to pipe 1: 1 event, for pipe {index}");
    }

    println!(
        "level-triggered, data not read, wait again: {} event(s)",
        kernel.wait().len()
    );

    kernel.read(1, 16);
    println!("after reading the data: {} event(s)", kernel.wait().len());
}

/// Repeats the edge-triggered measurement.
fn edge() {
    let mut kernel = Kernel::new(1);
    kernel.register(0, true);

    kernel.write(0, 5);
    let (first, second) = (kernel.wait().len(), kernel.wait().len());
    println!("edge-triggered, data not read: wait {first} event(s), wait again {second} event(s)");

    kernel.write(0, 5);
    println!(
        "edge-triggered, after another write: {} event(s)",
        kernel.wait().len()
    );
}

/// Compares the work of a wait with the work of a scan when 1000 pipes are
/// registered and 1 is ready.
fn many() {
    let mut kernel = Kernel::new(1000);

    for index in 0..1000 {
        kernel.register(index, false);
    }

    kernel.write(700, 5);

    if let [index] = kernel.wait().as_slice() {
        println!("1000 pipes registered, pipe 700 written: 1 event, for pipe {index}");
    }

    let by_wait = kernel.examined;
    kernel.scan();
    println!(
        "registrations examined: {by_wait} by the wait, {} by a scan",
        kernel.examined - by_wait
    );
}
// ANCHOR_END: measure

// ANCHOR: event_loop
impl Kernel {
    /// One iteration of an event loop: wait for ready pipes, then run the
    /// handler for each. Returns the pipes it handled.
    fn turn(&mut self, handle: fn(&mut Kernel, usize)) -> Vec<usize> {
        let events = self.wait();

        for &index in &events {
            handle(self, index);
        }

        events
    }
}

/// Formats pipe numbers the way Go prints a slice.
fn list(pipes: &[usize]) -> String {
    let words: Vec<String> = pipes.iter().map(usize::to_string).collect();

    format!("[{}]", words.join(" "))
}

/// Registers 4 pipes, writes to 2 of them, and runs an event loop whose
/// handler reads at most 4 bytes for each event.
fn event_loop() {
    let mut kernel = Kernel::new(4);

    for index in 0..4 {
        kernel.register(index, false);
    }

    kernel.write(2, 5);
    kernel.write(0, 3);

    let handle = |kernel: &mut Kernel, index: usize| {
        kernel.read(index, 4);
    };

    let turns = [
        kernel.turn(handle),
        kernel.turn(handle),
        kernel.turn(handle),
    ];

    println!(
        "event loop: turn 1 handles {}, turn 2 handles {}, turn 3 handles {}",
        list(&turns[0]),
        list(&turns[1]),
        list(&turns[2])
    );
}
// ANCHOR_END: event_loop

fn main() {
    level();
    edge();
    many();
    event_loop();
}
