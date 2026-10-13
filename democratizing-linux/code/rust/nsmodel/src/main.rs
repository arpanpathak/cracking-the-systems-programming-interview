//! Models 2 kinds of namespace. A PID namespace gives its processes their own
//! process numbers, and every process also has a number in each enclosing
//! namespace. A UTS namespace holds a host name.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p nsmodel
//! ```

// ANCHOR: types
/// Hands out process numbers. `level` is its depth below the root namespace,
/// which has level 0. `parent` is the index of the enclosing namespace.
struct PidNamespace {
    parent: Option<usize>,
    level: usize,
    last: u32,
}

/// A process belongs to one namespace of each kind, named here by its index
/// in the kernel's tables. `numbers` holds its process number in every PID
/// namespace from the root, at index 0, down to its own.
struct Process {
    pid: usize,
    uts: usize,
    numbers: Vec<u32>,
}

/// The namespaces of a machine. A UTS namespace is the host name that its
/// processes see.
struct Kernel {
    pid_namespaces: Vec<PidNamespace>,
    hostnames: Vec<String>,
}

impl Kernel {
    /// Returns the next unused number of a PID namespace.
    fn allocate(&mut self, namespace: usize) -> u32 {
        self.pid_namespaces[namespace].last += 1;

        self.pid_namespaces[namespace].last
    }
}
// ANCHOR_END: types

// ANCHOR: fork
impl Kernel {
    /// Creates a child. By default the child is in its parent's namespaces.
    /// With `new_pid` it is the first process of a new PID namespace below
    /// the parent's. With `new_uts` it gets a copy of the parent's UTS
    /// namespace.
    fn fork(&mut self, parent: &Process, new_pid: bool, new_uts: bool) -> Process {
        let (mut pid, mut uts) = (parent.pid, parent.uts);

        if new_pid {
            self.pid_namespaces.push(PidNamespace {
                parent: Some(parent.pid),
                level: self.pid_namespaces[parent.pid].level + 1,
                last: 0,
            });
            pid = self.pid_namespaces.len() - 1;
        }

        if new_uts {
            self.hostnames.push(self.hostnames[parent.uts].clone());
            uts = self.hostnames.len() - 1;
        }

        let mut numbers = vec![0; self.pid_namespaces[pid].level + 1];
        let mut namespace = Some(pid);

        while let Some(current) = namespace {
            numbers[self.pid_namespaces[current].level] = self.allocate(current);
            namespace = self.pid_namespaces[current].parent;
        }

        Process { pid, uts, numbers }
    }
}
// ANCHOR_END: fork

// ANCHOR: visible
impl Kernel {
    /// Returns the number by which a process is known in a namespace. A
    /// process is visible in its own PID namespace and in every namespace
    /// that encloses it, and in no other.
    fn number_in(&self, process: &Process, namespace: usize) -> Option<u32> {
        let level = self.pid_namespaces[namespace].level;
        let mut own = Some(process.pid);

        while let Some(current) = own
            && self.pid_namespaces[current].level > level
        {
            own = self.pid_namespaces[current].parent;
        }

        if own != Some(namespace) {
            return None;
        }

        process.numbers.get(level).copied()
    }

    /// Describes a process as a namespace sees it.
    fn seen(&self, process: &Process, namespace: usize) -> String {
        match self.number_in(process, namespace) {
            Some(number) => format!("pid {number}"),
            None => "not visible".to_owned(),
        }
    }
}
// ANCHOR_END: visible

// ANCHOR: trace
/// Formats numbers the way Go prints a slice.
fn list(numbers: &[u32]) -> String {
    let words: Vec<String> = numbers.iter().map(u32::to_string).collect();

    format!("[{}]", words.join(" "))
}

fn main() {
    let root = PidNamespace {
        parent: None,
        level: 0,
        last: 0,
    };

    let mut kernel = Kernel {
        pid_namespaces: vec![root],
        hostnames: vec!["host".to_owned()],
    };

    let first = Process {
        pid: 0,
        uts: 0,
        numbers: vec![kernel.allocate(0)],
    };

    let shell = kernel.fork(&first, false, false);
    let a = kernel.fork(&shell, true, true);
    let child = kernel.fork(&a, false, false);
    let b = kernel.fork(&shell, true, true);
    let nested = kernel.fork(&child, true, false);

    let rows = [
        ("first process", &first),
        ("shell", &shell),
        ("first process of A", &a),
        ("its child", &child),
        ("first process of B", &b),
        ("nested below A", &nested),
    ];

    for (name, process) in rows {
        println!(
            "{name:<20} numbers from the root namespace down: {}",
            list(&process.numbers)
        );
    }

    println!(
        "the first process of B, seen from the root namespace: {}",
        kernel.seen(&b, 0)
    );
    println!(
        "the first process of B, seen from A: {}",
        kernel.seen(&b, a.pid)
    );
    println!("the shell, seen from A: {}", kernel.seen(&shell, a.pid));
    println!(
        "the nested process, seen from A: {}",
        kernel.seen(&nested, a.pid)
    );

    kernel.hostnames[a.uts] = "box".to_owned();
    println!(
        "host name set to \"box\" in A: A sees {:?}, its child {:?}, B {:?}, the shell {:?}",
        kernel.hostnames[a.uts],
        kernel.hostnames[child.uts],
        kernel.hostnames[b.uts],
        kernel.hostnames[shell.uts]
    );
}
// ANCHOR_END: trace
