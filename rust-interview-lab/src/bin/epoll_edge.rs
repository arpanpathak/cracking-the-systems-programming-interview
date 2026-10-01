//! Edge-triggered epoll: what it reports, and the handler it needs.
//!
//! Level-triggered epoll reports a socket for as long as it has data.
//! Edge-triggered epoll reports it once per arrival, so a handler that leaves
//! data behind never hears about it again. The program also shows
//! `EPOLLONESHOT`, which disables a descriptor after one event, and
//! `EPOLLEXCLUSIVE`, which wakes one waiter instead of all of them.
//!
//! Linux only. Run with: cargo run --bin epoll_edge

#[cfg(target_os = "linux")]
mod linux {
    use std::{
        io::{self, Read, Write},
        net::{TcpListener, TcpStream},
        os::{
            fd::{AsRawFd, FromRawFd, OwnedFd, RawFd},
            unix::net::UnixStream,
        },
        sync::{Arc, Barrier},
        thread,
        time::Duration,
    };

    /// How long `epoll_wait` waits before the program decides no event is coming.
    const QUIET_MS: i32 = 100;

    /// An epoll instance. Closed when dropped.
    pub struct Epoll(OwnedFd);

    impl Epoll {
        pub fn new() -> io::Result<Self> {
            // SAFETY: epoll_create1 takes no pointers, and the result is checked.
            let fd = unsafe { libc::epoll_create1(libc::EPOLL_CLOEXEC) };
            if fd < 0 {
                return Err(io::Error::last_os_error());
            }
            // SAFETY: the descriptor was just created, and nothing else owns it.
            Ok(Self(unsafe { OwnedFd::from_raw_fd(fd) }))
        }

        fn control(&self, op: libc::c_int, fd: RawFd, flags: u32) -> io::Result<()> {
            let mut event = libc::epoll_event {
                events: flags,
                u64: fd as u64,
            };
            // SAFETY: `event` is a valid epoll_event that outlives the call.
            let result = unsafe { libc::epoll_ctl(self.0.as_raw_fd(), op, fd, &mut event) };
            if result < 0 {
                return Err(io::Error::last_os_error());
            }
            Ok(())
        }

        /// Add `fd` to the interest list.
        pub fn add(&self, fd: RawFd, flags: u32) -> io::Result<()> {
            self.control(libc::EPOLL_CTL_ADD, fd, flags)
        }

        /// Change the flags of `fd`. This also re-arms an `EPOLLONESHOT` descriptor.
        pub fn modify(&self, fd: RawFd, flags: u32) -> io::Result<()> {
            self.control(libc::EPOLL_CTL_MOD, fd, flags)
        }

        /// Wait up to `timeout_ms` and return the number of events.
        pub fn wait(&self, timeout_ms: i32) -> io::Result<usize> {
            let mut events = [libc::epoll_event { events: 0, u64: 0 }; 8];
            // SAFETY: `events` is a writable buffer of 8 entries.
            let ready =
                unsafe { libc::epoll_wait(self.0.as_raw_fd(), events.as_mut_ptr(), 8, timeout_ms) };
            if ready < 0 {
                return Err(io::Error::last_os_error());
            }
            Ok(ready as usize)
        }
    }

    /// Read once, at most 4,096 bytes, and return how many arrived.
    pub fn read_once(socket: &mut UnixStream) -> io::Result<usize> {
        let mut buffer = [0; 4096];
        socket.read(&mut buffer)
    }

    /// Read until the socket has nothing left (`EAGAIN`), and return the total.
    pub fn read_until_eagain(socket: &mut UnixStream) -> io::Result<usize> {
        let mut buffer = [0; 4096];
        let mut total = 0;
        loop {
            match socket.read(&mut buffer) {
                Ok(0) => return Ok(total),
                Ok(read) => total += read,
                Err(error) if error.kind() == io::ErrorKind::WouldBlock => return Ok(total),
                Err(error) => return Err(error),
            }
        }
    }

    /// Write `sent` bytes into one end of a socket pair. Then wait on the other
    /// end with `flags`, and call `handler` once per event, until no event comes.
    /// Returns the bytes `handler` read at each event.
    pub fn run(
        flags: u32,
        sent: usize,
        handler: fn(&mut UnixStream) -> io::Result<usize>,
    ) -> io::Result<Vec<usize>> {
        let (mut writer, mut reader) = UnixStream::pair()?;
        reader.set_nonblocking(true)?;
        let epoll = Epoll::new()?;
        epoll.add(reader.as_raw_fd(), flags)?;
        writer.write_all(&vec![b'x'; sent])?;

        let mut per_event = Vec::new();
        while epoll.wait(QUIET_MS)? > 0 {
            per_event.push(handler(&mut reader)?);
        }
        Ok(per_event)
    }

    /// Events seen with `EPOLLONESHOT`: after the first write, after a second
    /// write, and after re-arming the descriptor.
    pub fn oneshot() -> io::Result<[usize; 3]> {
        let (mut writer, mut reader) = UnixStream::pair()?;
        reader.set_nonblocking(true)?;
        let epoll = Epoll::new()?;
        let flags = (libc::EPOLLIN | libc::EPOLLET | libc::EPOLLONESHOT) as u32;
        epoll.add(reader.as_raw_fd(), flags)?;

        writer.write_all(b"first")?;
        let first = epoll.wait(QUIET_MS)?;
        read_until_eagain(&mut reader)?;

        writer.write_all(b"second")?;
        let before_rearm = epoll.wait(QUIET_MS)?;
        epoll.modify(reader.as_raw_fd(), flags)?;
        let after_rearm = epoll.wait(QUIET_MS)?;
        Ok([first, before_rearm, after_rearm])
    }

    /// Start `waiters` threads, each blocked in `epoll_wait` on its own epoll
    /// instance that watches one shared listener. Connect one client, and
    /// return how many threads woke.
    pub fn woken_by_one_connection(waiters: usize, exclusive: bool) -> io::Result<usize> {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        listener.set_nonblocking(true)?;
        let fd = listener.as_raw_fd();
        let flags = if exclusive {
            (libc::EPOLLIN | libc::EPOLLEXCLUSIVE) as u32
        } else {
            libc::EPOLLIN as u32
        };

        let registered = Arc::new(Barrier::new(waiters + 1));
        let threads: Vec<_> = (0..waiters)
            .map(|_| {
                let registered = Arc::clone(&registered);
                thread::spawn(move || -> io::Result<bool> {
                    let epoll = Epoll::new()?;
                    epoll.add(fd, flags)?;
                    registered.wait();
                    Ok(epoll.wait(500)? > 0)
                })
            })
            .collect();

        registered.wait();
        thread::sleep(Duration::from_millis(50));
        let _client = TcpStream::connect(listener.local_addr()?)?;

        let mut woken = 0;
        for thread in threads {
            if thread.join().expect("waiter thread")? {
                woken += 1;
            }
        }
        Ok(woken)
    }
}

#[cfg(target_os = "linux")]
fn main() -> std::io::Result<()> {
    use linux::{read_once, read_until_eagain, run};

    const SENT: usize = 10_000;
    let level = libc::EPOLLIN as u32;
    let edge = (libc::EPOLLIN | libc::EPOLLET) as u32;

    println!("{SENT} bytes written into a socket; one handler call per epoll event\n");
    let runs = [
        ("level-triggered, read once ", run(level, SENT, read_once)?),
        ("edge-triggered,  read once ", run(edge, SENT, read_once)?),
        (
            "edge-triggered,  to EAGAIN ",
            run(edge, SENT, read_until_eagain)?,
        ),
    ];
    for (name, per_event) in runs {
        let left = SENT - per_event.iter().sum::<usize>();
        println!(
            "{name} events {}, bytes per event {per_event:?}, left unread {left}",
            per_event.len()
        );
    }

    let [first, before, after] = linux::oneshot()?;
    println!(
        "\nEPOLLONESHOT: first write {first} event, second write {before} events, \
         after re-arming {after} event"
    );

    println!("\n4 threads wait on one listener, and one client connects:");
    println!(
        "  without EPOLLEXCLUSIVE: {} threads woke",
        linux::woken_by_one_connection(4, false)?
    );
    println!(
        "  with EPOLLEXCLUSIVE:    {} thread woke",
        linux::woken_by_one_connection(4, true)?
    );
    Ok(())
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("epoll_edge uses Linux epoll; run it on Linux");
}

#[cfg(all(test, target_os = "linux"))]
mod tests {
    use super::linux::*;

    const LEVEL: u32 = libc::EPOLLIN as u32;
    const EDGE: u32 = (libc::EPOLLIN | libc::EPOLLET) as u32;

    #[test]
    fn level_triggered_reports_until_the_data_is_gone() {
        assert_eq!(
            run(LEVEL, 10_000, read_once).expect("run"),
            [4096, 4096, 1808]
        );
    }

    #[test]
    fn edge_triggered_with_one_read_leaves_data_behind() {
        assert_eq!(run(EDGE, 10_000, read_once).expect("run"), [4096]);
    }

    #[test]
    fn edge_triggered_drained_to_eagain_reads_everything() {
        assert_eq!(run(EDGE, 10_000, read_until_eagain).expect("run"), [10_000]);
    }

    #[test]
    fn oneshot_waits_for_a_rearm() {
        assert_eq!(oneshot().expect("oneshot"), [1, 0, 1]);
    }
}
