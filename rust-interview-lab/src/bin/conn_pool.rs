//! A client connection pool: at most `max` connections to one server, each
//! lent out behind a guard that gives it back when dropped. Idle connections
//! are reused, closed after `idle_timeout`, and checked before reuse in case
//! the server closed them first.
//!
//! Run with: cargo run --release --bin conn_pool

use std::{
    io::{self, BufRead, BufReader, ErrorKind, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    ops::{Deref, DerefMut},
    sync::{
        Arc,
        Condvar,
        Mutex,
        atomic::{AtomicUsize, Ordering::Relaxed},
    },
    thread,
    time::{Duration, Instant},
};

/// The limits a pool enforces.
#[derive(Clone, Copy)]
struct Config {
    /// The most connections open at once, lent out or idle.
    max: usize,
    /// How long `get` waits for a connection before it gives up.
    wait_timeout: Duration,
    /// How long a connection may sit idle before the pool closes it.
    idle_timeout: Duration,
    /// Whether to check that an idle connection is still open before lending it.
    check_alive: bool,
}

/// What the pool has done, for the demonstration.
#[derive(Default)]
struct Stats {
    connects: AtomicUsize,
    reuses: AtomicUsize,
    evicted: AtomicUsize,
    stale: AtomicUsize,
}

struct Idle {
    stream: TcpStream,
    since: Instant,
}

/// The connections the pool owns: the idle ones, and a count of all open ones.
struct State {
    idle: Vec<Idle>,
    open: usize,
}

struct Pool {
    address: SocketAddr,
    config: Config,
    state: Mutex<State>,
    returned: Condvar,
    stats: Stats,
}

/// A connection lent out by the pool. Dropping it gives it back.
struct Pooled<'a> {
    pool: &'a Pool,
    stream: Option<TcpStream>,
    broken: bool,
}

/// Whether the server has closed `stream`, checked without blocking: a
/// readable socket with nothing to read has seen the server's `FIN`.
fn is_alive(stream: &TcpStream) -> bool {
    if stream.set_nonblocking(true).is_err() {
        return false;
    }
    let alive = match stream.peek(&mut [0]) {
        Err(error) => error.kind() == ErrorKind::WouldBlock,
        Ok(_) => false,
    };
    stream.set_nonblocking(false).is_ok() && alive
}

impl Pool {
    fn new(address: SocketAddr, config: Config) -> Self {
        Self {
            address,
            config,
            state: Mutex::new(State {
                idle: Vec::new(),
                open: 0,
            }),
            returned: Condvar::new(),
            stats: Stats::default(),
        }
    }

    /// Lend a connection: an idle one if there is one, a new one if the pool
    /// is below `max`, or the next one returned, waiting up to `wait_timeout`.
    fn get(&self) -> io::Result<Pooled<'_>> {
        let deadline = Instant::now() + self.config.wait_timeout;
        let mut state = self.state.lock().expect("pool lock");
        loop {
            if let Some(stream) = self.take_idle(&mut state) {
                self.stats.reuses.fetch_add(1, Relaxed);
                return Ok(self.lend(stream));
            }
            if state.open < self.config.max {
                state.open += 1;
                drop(state);
                return self.connect();
            }
            let now = Instant::now();
            if now >= deadline {
                return Err(io::Error::new(ErrorKind::TimedOut, "pool exhausted"));
            }
            state = self
                .returned
                .wait_timeout(state, deadline - now)
                .expect("pool lock")
                .0;
        }
    }

    /// The most recently returned idle connection that is fresh and open.
    /// Connections idle too long, or closed by the server, are dropped.
    fn take_idle(&self, state: &mut State) -> Option<TcpStream> {
        while let Some(idle) = state.idle.pop() {
            if idle.since.elapsed() > self.config.idle_timeout {
                state.open -= 1;
                self.stats.evicted.fetch_add(1, Relaxed);
            } else if self.config.check_alive && !is_alive(&idle.stream) {
                state.open -= 1;
                self.stats.stale.fetch_add(1, Relaxed);
            } else {
                return Some(idle.stream);
            }
        }
        None
    }

    /// Open a new connection. The slot was reserved under the lock, and the
    /// connect runs outside it, so other callers are not held up.
    fn connect(&self) -> io::Result<Pooled<'_>> {
        match TcpStream::connect(self.address) {
            Ok(stream) => {
                self.stats.connects.fetch_add(1, Relaxed);
                Ok(self.lend(stream))
            }
            Err(error) => {
                self.release_slot();
                Err(error)
            }
        }
    }

    fn lend(&self, stream: TcpStream) -> Pooled<'_> {
        Pooled {
            pool: self,
            stream: Some(stream),
            broken: false,
        }
    }

    /// Take back a connection. A broken one is closed, and its slot is freed.
    fn give_back(&self, stream: TcpStream, broken: bool) {
        if broken {
            return self.release_slot();
        }
        let mut state = self.state.lock().expect("pool lock");
        state.idle.push(Idle {
            stream,
            since: Instant::now(),
        });
        drop(state);
        self.returned.notify_one();
    }

    fn release_slot(&self) {
        self.state.lock().expect("pool lock").open -= 1;
        self.returned.notify_one();
    }

    /// (open connections, idle connections)
    fn sizes(&self) -> (usize, usize) {
        let state = self.state.lock().expect("pool lock");
        (state.open, state.idle.len())
    }
}

impl Pooled<'_> {
    /// Close this connection instead of returning it, after an error.
    fn discard(mut self) {
        self.broken = true;
    }
}

impl Deref for Pooled<'_> {
    type Target = TcpStream;

    fn deref(&self) -> &TcpStream {
        self.stream.as_ref().expect("stream until drop")
    }
}

impl DerefMut for Pooled<'_> {
    fn deref_mut(&mut self) -> &mut TcpStream {
        self.stream.as_mut().expect("stream until drop")
    }
}

impl Drop for Pooled<'_> {
    fn drop(&mut self) {
        if let Some(stream) = self.stream.take() {
            self.pool.give_back(stream, self.broken);
        }
    }
}

/// Send one line, and read one line back.
fn request(stream: &mut TcpStream, line: &str) -> io::Result<String> {
    writeln!(stream, "{line}")?;
    let mut reply = String::new();
    if BufReader::new(&*stream).read_line(&mut reply)? == 0 {
        return Err(io::Error::new(
            ErrorKind::UnexpectedEof,
            "server closed the connection",
        ));
    }
    Ok(reply.trim_end().to_string())
}

/// One request on a pooled connection. A connection that failed is discarded,
/// so the pool does not lend it again.
fn ask(pool: &Pool, line: &str) -> io::Result<String> {
    let mut connection = pool.get()?;
    let reply = request(&mut connection, line);
    if reply.is_err() {
        connection.discard();
    }
    reply
}

/// A line server on loopback that closes a connection idle for `idle_close`.
/// Returns its address and a count of the connections it has accepted.
fn start_server(idle_close: Duration) -> io::Result<(SocketAddr, Arc<AtomicUsize>)> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let address = listener.local_addr()?;
    let accepted = Arc::new(AtomicUsize::new(0));
    let counter = Arc::clone(&accepted);
    thread::spawn(move || {
        for stream in listener.incoming().flatten() {
            counter.fetch_add(1, Relaxed);
            thread::spawn(move || serve(stream, idle_close));
        }
    });
    Ok((address, accepted))
}

/// Answer each line with "ok", until the client closes or stays quiet too long.
fn serve(stream: TcpStream, idle_close: Duration) -> io::Result<()> {
    stream.set_read_timeout(Some(idle_close))?;
    let mut writer = stream.try_clone()?;
    for line in BufReader::new(stream).lines() {
        let line = line?;
        writeln!(writer, "ok {line}")?;
    }
    Ok(())
}

fn main() -> io::Result<()> {
    const REQUESTS: usize = 2_000;
    const THREADS: usize = 8;
    let config = Config {
        max: 4,
        wait_timeout: Duration::from_secs(1),
        idle_timeout: Duration::from_secs(30),
        check_alive: true,
    };

    println!("1. {REQUESTS} requests from {THREADS} threads");
    let (address, accepted) = start_server(Duration::from_secs(30))?;
    let start = Instant::now();
    thread::scope(|scope| {
        for _ in 0..THREADS {
            scope.spawn(|| -> io::Result<()> {
                for _ in 0..REQUESTS / THREADS {
                    request(&mut TcpStream::connect(address)?, "ping")?;
                }
                Ok(())
            });
        }
    });
    println!(
        "  a new connection each:  {:>5} connections, {:>6.1} ms",
        accepted.load(Relaxed),
        start.elapsed().as_secs_f64() * 1000.0
    );

    let (address, accepted) = start_server(Duration::from_secs(30))?;
    let pool = Pool::new(address, config);
    let start = Instant::now();
    thread::scope(|scope| {
        for _ in 0..THREADS {
            scope.spawn(|| -> io::Result<()> {
                for _ in 0..REQUESTS / THREADS {
                    ask(&pool, "ping")?;
                }
                Ok(())
            });
        }
    });
    println!(
        "  a pool of {}:            {:>5} connections, {:>6.1} ms, {} reuses",
        config.max,
        accepted.load(Relaxed),
        start.elapsed().as_secs_f64() * 1000.0,
        pool.stats.reuses.load(Relaxed)
    );

    println!("\n2. The bound: 2 connections, both lent out");
    let pool = Pool::new(
        address,
        Config {
            max: 2,
            wait_timeout: Duration::from_millis(100),
            ..config
        },
    );
    let (first, second) = (pool.get()?, pool.get()?);
    let start = Instant::now();
    let third = pool.get().map(|_| ());
    println!(
        "  third get after {:.0} ms: {third:?}",
        start.elapsed().as_secs_f64() * 1000.0
    );
    drop(first);
    let fourth = pool.get().map(|_| ());
    println!(
        "  after one is returned: {fourth:?}, sizes (open, idle) = {:?}",
        pool.sizes()
    );
    drop(second);

    println!("\n3. Idle eviction: idle_timeout 100 ms");
    let pool = Pool::new(
        address,
        Config {
            idle_timeout: Duration::from_millis(100),
            ..config
        },
    );
    ask(&pool, "first")?;
    thread::sleep(Duration::from_millis(150));
    ask(&pool, "second")?;
    println!(
        "  connects {}, evicted {}",
        pool.stats.connects.load(Relaxed),
        pool.stats.evicted.load(Relaxed)
    );

    println!("\n4. A server that closes idle connections after 50 ms");
    let (address, _) = start_server(Duration::from_millis(50))?;
    for check_alive in [false, true] {
        let pool = Pool::new(
            address,
            Config {
                check_alive,
                ..config
            },
        );
        ask(&pool, "first")?;
        thread::sleep(Duration::from_millis(100));
        let outcome = ask(&pool, "second");
        println!(
            "  check_alive {check_alive:<5}: {outcome:?}, stale discarded {}",
            pool.stats.stale.load(Relaxed)
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn config(max: usize) -> Config {
        Config {
            max,
            wait_timeout: Duration::from_millis(50),
            idle_timeout: Duration::from_secs(30),
            check_alive: true,
        }
    }

    #[test]
    fn a_returned_connection_is_reused() {
        let (address, accepted) = start_server(Duration::from_secs(5)).unwrap();
        let pool = Pool::new(address, config(2));
        for _ in 0..10 {
            assert_eq!(request(&mut pool.get().unwrap(), "x").unwrap(), "ok x");
        }
        assert_eq!(accepted.load(Relaxed), 1);
        assert_eq!(pool.stats.reuses.load(Relaxed), 9);
    }

    #[test]
    fn the_pool_never_exceeds_max() {
        let (address, _) = start_server(Duration::from_secs(5)).unwrap();
        let pool = Pool::new(address, config(1));
        let held = pool.get().unwrap();
        let error = pool.get().map(|_| ()).unwrap_err();
        assert_eq!(error.kind(), ErrorKind::TimedOut);
        drop(held);
        assert!(pool.get().is_ok());
    }

    #[test]
    fn a_discarded_connection_frees_its_slot() {
        let (address, _) = start_server(Duration::from_secs(5)).unwrap();
        let pool = Pool::new(address, config(1));
        pool.get().unwrap().discard();
        assert_eq!(pool.sizes(), (0, 0));
        drop(pool.get().unwrap());
        assert_eq!(pool.stats.connects.load(Relaxed), 2);
    }
}
