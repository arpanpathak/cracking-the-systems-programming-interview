//! Models the signal state the kernel keeps for a process: a pending mask, a
//! blocked mask, and an action for each signal. It separates sending a signal
//! from delivering it, and shows what a delivered signal does to a process
//! that is blocked in a system call.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p sigmodel
//! ```

// ANCHOR: imports
use std::fmt;
// ANCHOR_END: imports

// ANCHOR: state
const SIGKILL: usize = 9;
const SIGUSR1: usize = 10;
const SIGTERM: usize = 15;
const SIGCHLD: usize = 17;
const SIGLAST: usize = 64;

#[derive(Clone, Copy, PartialEq)]
enum Action {
    Default,
    Ignore,
    Handle,
}

#[derive(Debug)]
struct Invalid;

impl fmt::Display for Invalid {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("EINVAL")
    }
}

/// The signal state of one process. Signal `n` is bit `n - 1` of the masks.
struct Process {
    pending: u64,
    blocked: u64,
    actions: [Action; SIGLAST + 1],
    restart: [bool; SIGLAST + 1],
    handled: u32,
    killed_by: Option<usize>,

    /// The system call the process is blocked in, or `None` when it is
    /// running. `outcome` records what a signal did to that call.
    call: Option<&'static str>,
    outcome: String,
}

fn bit(signal: usize) -> u64 {
    1 << (signal - 1)
}

impl Process {
    fn new(call: Option<&'static str>) -> Process {
        Process {
            pending: 0,
            blocked: 0,
            actions: [Action::Default; SIGLAST + 1],
            restart: [false; SIGLAST + 1],
            handled: 0,
            killed_by: None,
            call,
            outcome: String::new(),
        }
    }
}
// ANCHOR_END: state

// ANCHOR: control
impl Process {
    /// Installs an action for a signal. `restart` is the `SA_RESTART` flag of
    /// a handler. The action of `SIGKILL` cannot be changed.
    fn set_action(&mut self, signal: usize, action: Action, restart: bool) -> Result<(), Invalid> {
        if signal == SIGKILL {
            return Err(Invalid);
        }

        self.actions[signal] = action;
        self.restart[signal] = restart;

        Ok(())
    }

    /// Adds signals to the blocked mask. `SIGKILL` is removed from the
    /// request without an error, as the kernel does.
    fn block(&mut self, mask: u64) {
        self.blocked |= mask & !bit(SIGKILL);
    }

    /// Removes signals from the blocked mask and delivers what was waiting
    /// for it.
    fn unblock(&mut self, mask: u64) {
        self.blocked &= !mask;
        self.deliver();
    }
}
// ANCHOR_END: control

// ANCHOR: send
impl Process {
    /// Reports whether a signal would be discarded on delivery: its action is
    /// ignore, or its action is the default and the default is to ignore,
    /// which is the case for `SIGCHLD`.
    fn ignored(&self, signal: usize) -> bool {
        match self.actions[signal] {
            Action::Ignore => true,
            Action::Default => signal == SIGCHLD,
            Action::Handle => false,
        }
    }

    /// The sender's half. It discards a signal that the target ignores and
    /// does not block. Otherwise it sets the pending bit, which is already
    /// set when the same signal is waiting.
    fn send(&mut self, signal: usize) {
        if self.ignored(signal) && self.blocked & bit(signal) == 0 {
            return;
        }

        self.pending |= bit(signal);
    }
}
// ANCHOR_END: send

// ANCHOR: deliver
impl Process {
    /// The target's half. The kernel runs it when the process is about to
    /// return to user mode. It takes each pending signal that is not blocked,
    /// lowest number first, and performs its action.
    fn deliver(&mut self) {
        for signal in 1..=SIGLAST {
            if self.killed_by.is_some() {
                break;
            }

            if self.pending & !self.blocked & bit(signal) == 0 {
                continue;
            }

            self.pending &= !bit(signal);

            if self.actions[signal] == Action::Handle {
                self.handled += 1;
                self.interrupt(signal);
            } else if !self.ignored(signal) {
                self.killed_by = Some(signal);
            }
        }
    }

    /// Decides what happens to a blocking system call when a handler has run:
    /// the call is restarted, or it fails with `EINTR`.
    fn interrupt(&mut self, signal: usize) {
        let Some(call) = self.call else {
            return;
        };

        if self.restart[signal] {
            self.outcome = format!("the {call} is restarted");

            return;
        }

        self.outcome = format!("the {call} fails with EINTR");
        self.call = None;
    }
}
// ANCHOR_END: deliver

// ANCHOR: trace
fn coalescing() -> Result<(), Invalid> {
    let mut process = Process::new(None);

    process.set_action(SIGUSR1, Action::Handle, false)?;
    process.block(bit(SIGUSR1));

    for _ in 0..3 {
        process.send(SIGUSR1);
        process.deliver();
    }

    println!(
        "SIGUSR1 blocked and sent 3 times: pending mask {:#x}",
        process.pending
    );

    process.unblock(bit(SIGUSR1));
    println!(
        "after unblocking the handler ran {} time(s)",
        process.handled
    );

    Ok(())
}

fn ignoring() -> Result<(), Invalid> {
    let mut process = Process::new(None);

    process.set_action(SIGTERM, Action::Ignore, false)?;
    process.send(SIGTERM);
    println!(
        "SIGTERM ignored and sent: pending mask {:#x}",
        process.pending
    );

    if let Err(error) = process.set_action(SIGKILL, Action::Handle, false) {
        println!("installing a handler for SIGKILL: {error}");
    }

    process.block(u64::MAX);
    process.send(SIGKILL);
    process.deliver();

    if let Some(signal) = process.killed_by {
        println!("every signal blocked, SIGKILL sent: killed by signal {signal}");
    }

    Ok(())
}

fn interrupting(restart: bool) -> Result<(), Invalid> {
    let mut process = Process::new(Some("read"));

    process.set_action(SIGUSR1, Action::Handle, restart)?;
    process.send(SIGUSR1);
    process.deliver();

    println!(
        "handler runs during a blocking read, SA_RESTART {restart}: {}",
        process.outcome
    );

    Ok(())
}

fn main() -> Result<(), Invalid> {
    coalescing()?;
    ignoring()?;
    interrupting(false)?;
    interrupting(true)
}
// ANCHOR_END: trace
