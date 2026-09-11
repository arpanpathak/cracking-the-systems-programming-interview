//! A minimal async runtime, built from `Future`, `Waker`, and `Pin`.
//!
//! `.await` is not magic. A `Future` is a state machine with one method, `poll`,
//! that returns `Ready(value)` or `Pending`; when it returns `Pending` it must
//! arrange for the `Waker` in its `Context` to be called later. An executor is a
//! loop that polls tasks and parks until a waker fires.
//!
//! This module implements that loop twice, from scratch and without a runtime
//! dependency:
//!
//! - [`block_on`] drives one future on the current thread, parking on `Pending`;
//! - [`MiniExecutor`] queues independent tasks and re-enqueues them when woken.
//!
//! It is deliberately small. What it makes concrete is the part interviewers ask
//! about: why `poll` takes `Pin<&mut Self>`, what `Pending` promises, and where
//! `Send` matters for a multi-threaded runtime.

use std::collections::VecDeque;
use std::future::Future;
use std::pin::Pin;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::task::{Context, Poll, Wake, Waker};
use std::thread;
use std::time::Duration;

/// Block the current thread until `future` completes.
///
/// The future is pinned on the heap so its address is stable across `await`
/// points, and the thread parks whenever the future reports `Pending`. The waker
/// unparks it, so the loop polls again only when there is a reason to.
pub fn block_on<F: Future>(future: F) -> F::Output {
    let mut future = Box::pin(future);
    let waker = Waker::from(Arc::new(ThreadWaker(thread::current())));
    let mut context = Context::from_waker(&waker);

    loop {
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => return value,
            // `park` may return spuriously, so the loop re-polls either way.
            Poll::Pending => thread::park(),
        }
    }
}

/// Waker that unparks the thread which is driving the future.
struct ThreadWaker(thread::Thread);

impl Wake for ThreadWaker {
    fn wake(self: Arc<Self>) {
        self.0.unpark();
    }

    fn wake_by_ref(self: &Arc<Self>) {
        self.0.unpark();
    }
}

/// A future that yields to the executor `times` times before completing.
///
/// Completes with the number of times it yielded, which makes it easy to assert
/// that a runtime actually suspended and resumed a task.
pub struct YieldTimes {
    remaining: usize,
    yielded: usize,
}

impl YieldTimes {
    pub fn new(times: usize) -> Self {
        Self {
            remaining: times,
            yielded: 0,
        }
    }
}

impl Future for YieldTimes {
    type Output = usize;

    fn poll(self: Pin<&mut Self>, context: &mut Context<'_>) -> Poll<usize> {
        // `YieldTimes` is `Unpin`, so a mutable reference is safe to take.
        let this = self.get_mut();
        if this.remaining == 0 {
            return Poll::Ready(this.yielded);
        }

        this.remaining -= 1;
        this.yielded += 1;
        // Ask to be polled again; an executor that ignores this hangs.
        context.waker().wake_by_ref();
        Poll::Pending
    }
}

struct DelayState {
    ready: bool,
    waker: Option<Waker>,
}

/// A future that completes after a wall-clock duration.
///
/// A background thread sleeps and then wakes the task. Storing and waking the
/// [`Waker`] — rather than spinning in `poll` — is the whole point: `poll` never
/// blocks the executor thread.
pub struct Delay {
    state: Arc<Mutex<DelayState>>,
}

impl Delay {
    pub fn new(duration: Duration) -> Self {
        let state = Arc::new(Mutex::new(DelayState {
            ready: false,
            waker: None,
        }));

        let thread_state = Arc::clone(&state);
        thread::spawn(move || {
            thread::sleep(duration);
            let waker = {
                let mut guard = thread_state.lock().expect("delay mutex poisoned");
                guard.ready = true;
                guard.waker.take()
            };
            if let Some(waker) = waker {
                waker.wake();
            }
        });

        Self { state }
    }
}

impl Future for Delay {
    type Output = ();

    fn poll(self: Pin<&mut Self>, context: &mut Context<'_>) -> Poll<()> {
        let mut guard = self.state.lock().expect("delay mutex poisoned");
        if guard.ready {
            Poll::Ready(())
        } else {
            guard.waker = Some(context.waker().clone());
            Poll::Pending
        }
    }
}

struct Task {
    future: Mutex<Pin<Box<dyn Future<Output = ()> + Send>>>,
    queue: Arc<Mutex<VecDeque<Arc<Task>>>>,
    completed: AtomicBool,
}

impl Wake for Task {
    fn wake(self: Arc<Self>) {
        // Re-enqueue the task. Cloning the `Arc` is a refcount bump, not a deep copy.
        self.queue
            .lock()
            .expect("executor queue poisoned")
            .push_back(Arc::clone(&self));
    }

    fn wake_by_ref(self: &Arc<Self>) {
        self.queue
            .lock()
            .expect("executor queue poisoned")
            .push_back(Arc::clone(self));
    }
}

/// A single-threaded, `Send`-only executor.
///
/// Real runtimes add work stealing, timers, and I/O readiness. This keeps only the
/// part that matters for explaining how `.await` makes progress: a queue of tasks
/// where waking a task puts it back on the queue.
#[derive(Default)]
pub struct MiniExecutor {
    queue: Arc<Mutex<VecDeque<Arc<Task>>>>,
}

impl MiniExecutor {
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a task to the executor.
    pub fn spawn<F>(&self, future: F)
    where
        F: Future<Output = ()> + Send + 'static,
    {
        let task = Arc::new(Task {
            future: Mutex::new(Box::pin(future)),
            queue: Arc::clone(&self.queue),
            completed: AtomicBool::new(false),
        });
        self.queue
            .lock()
            .expect("executor queue poisoned")
            .push_back(task);
    }

    /// Run until the queue is empty.
    ///
    /// A task that returns `Pending` without waking stays suspended, which is why
    /// this returns rather than blocks: a runtime with timers or I/O would also
    /// park on an event source.
    pub fn run(&self) {
        loop {
            let Some(task) = self
                .queue
                .lock()
                .expect("executor queue poisoned")
                .pop_front()
            else {
                return;
            };

            if task.completed.load(Ordering::Acquire) {
                continue;
            }

            let waker = Waker::from(Arc::clone(&task));
            let mut context = Context::from_waker(&waker);
            let mut future = task.future.lock().expect("task mutex poisoned");
            if future.as_mut().poll(&mut context).is_ready() {
                task.completed.store(true, Ordering::Release);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::AtomicUsize;
    use std::time::Instant;

    #[test]
    fn block_on_drives_a_hand_written_future() {
        assert_eq!(block_on(YieldTimes::new(3)), 3);
    }

    #[test]
    fn block_on_polls_an_async_block() {
        let total = block_on(async {
            let a = YieldTimes::new(1).await;
            let b = YieldTimes::new(2).await;
            a + b
        });
        assert_eq!(total, 3);
    }

    #[test]
    fn block_on_waits_for_a_delay() {
        let start = Instant::now();
        block_on(Delay::new(Duration::from_millis(30)));
        assert!(start.elapsed() >= Duration::from_millis(20));
    }

    #[test]
    fn executor_runs_spawned_tasks_to_completion() {
        let executor = MiniExecutor::new();
        let counter = Arc::new(AtomicUsize::new(0));

        for _ in 0..4 {
            let counter = Arc::clone(&counter);
            executor.spawn(async move {
                YieldTimes::new(2).await;
                counter.fetch_add(1, Ordering::SeqCst);
            });
        }

        executor.run();
        assert_eq!(counter.load(Ordering::SeqCst), 4);
    }

    #[test]
    fn executor_polls_an_immediately_ready_task() {
        let executor = MiniExecutor::new();
        let flag = Arc::new(AtomicBool::new(false));

        let task_flag = Arc::clone(&flag);
        executor.spawn(async move {
            task_flag.store(true, Ordering::SeqCst);
        });

        executor.run();
        assert!(flag.load(Ordering::SeqCst));
    }
}
