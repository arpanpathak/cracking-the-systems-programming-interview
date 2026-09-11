//! epoll echo server: one thread, many non-blocking sockets.
//!
//! Reads run until `EAGAIN`, and a reply that does not fit the socket buffer is
//! queued and finished under `EPOLLOUT`, so one slow client cannot stall the loop.
//! Linux only; kqueue and IOCP are the portable equivalents.

#[cfg(target_os = "linux")]
mod linux {
    use std::collections::HashMap;
    use std::io;
    use std::sync::atomic::{AtomicBool, Ordering};

    const MAX_EVENTS: usize = 64;
    const EPOLL_TIMEOUT_MS: i32 = 100;

    /// Per-connection state. `out`/`out_pos` form a write buffer that survives a
    /// partial write.
    #[derive(Default)]
    struct Connection {
        out: Vec<u8>,
        out_pos: usize,
    }

    impl Connection {
        fn has_pending_output(&self) -> bool {
            self.out_pos < self.out.len()
        }
    }

    /// Bind a non-blocking listener on `127.0.0.1:port`; port 0 asks the kernel for
    /// a free port, which is returned alongside the fd.
    pub fn bind_listener(port: u16) -> io::Result<(i32, u16)> {
        // SAFETY: all pointers are to stack values that outlive the call.
        unsafe {
            let fd = libc::socket(libc::AF_INET, libc::SOCK_STREAM | libc::SOCK_NONBLOCK, 0);
            if fd < 0 {
                return Err(io::Error::last_os_error());
            }

            let enable: libc::c_int = 1;
            if libc::setsockopt(
                fd,
                libc::SOL_SOCKET,
                libc::SO_REUSEADDR,
                &enable as *const _ as *const libc::c_void,
                std::mem::size_of::<libc::c_int>() as libc::socklen_t,
            ) < 0
            {
                let error = io::Error::last_os_error();
                libc::close(fd);
                return Err(error);
            }

            let mut address: libc::sockaddr_in = std::mem::zeroed();
            address.sin_family = libc::AF_INET as libc::sa_family_t;
            address.sin_port = port.to_be();
            address.sin_addr.s_addr = libc::INADDR_LOOPBACK.to_be();

            if libc::bind(
                fd,
                &address as *const _ as *const libc::sockaddr,
                std::mem::size_of::<libc::sockaddr_in>() as libc::socklen_t,
            ) < 0
            {
                let error = io::Error::last_os_error();
                libc::close(fd);
                return Err(error);
            }

            if libc::listen(fd, 128) < 0 {
                let error = io::Error::last_os_error();
                libc::close(fd);
                return Err(error);
            }

            let mut bound: libc::sockaddr_in = std::mem::zeroed();
            let mut length = std::mem::size_of::<libc::sockaddr_in>() as libc::socklen_t;
            if libc::getsockname(fd, &mut bound as *mut _ as *mut libc::sockaddr, &mut length) < 0 {
                let error = io::Error::last_os_error();
                libc::close(fd);
                return Err(error);
            }

            Ok((fd, u16::from_be(bound.sin_port)))
        }
    }

    /// Run the event loop until `shutdown` becomes true.
    pub fn event_loop(epfd: i32, listen_fd: i32, shutdown: &AtomicBool) -> io::Result<()> {
        epoll_add(epfd, listen_fd, libc::EPOLLIN as u32)?;

        let mut connections: HashMap<i32, Connection> = HashMap::new();
        let mut events = vec![libc::epoll_event { events: 0, u64: 0 }; MAX_EVENTS];

        while !shutdown.load(Ordering::Relaxed) {
            // SAFETY: `events` is a valid, writable buffer of MAX_EVENTS entries.
            let ready = unsafe {
                libc::epoll_wait(
                    epfd,
                    events.as_mut_ptr(),
                    events.len() as i32,
                    EPOLL_TIMEOUT_MS,
                )
            };

            if ready < 0 {
                let error = io::Error::last_os_error();
                if error.raw_os_error() == Some(libc::EINTR) {
                    continue;
                }
                return Err(error);
            }

            for event in &events[..ready as usize] {
                let fd = event.u64 as i32;
                if fd == listen_fd {
                    accept_ready(epfd, listen_fd, &mut connections)?;
                    continue;
                }

                let readable = event.events & (libc::EPOLLIN as u32) != 0;
                let writable = event.events & (libc::EPOLLOUT as u32) != 0;

                if readable && !read_into(fd, &mut connections)? {
                    continue; // connection closed
                }
                if writable && connections.contains_key(&fd) {
                    flush(fd, &mut connections)?;
                }
                if connections.contains_key(&fd) {
                    update_interest(epfd, fd, &mut connections)?;
                }
            }
        }

        Ok(())
    }

    /// Accept every pending connection, then return; `accept4` with
    /// `SOCK_NONBLOCK` means a client socket can never block the loop.
    fn accept_ready(
        epfd: i32,
        listen_fd: i32,
        connections: &mut HashMap<i32, Connection>,
    ) -> io::Result<()> {
        loop {
            // SAFETY: a null sockaddr is explicitly allowed for accept.
            let client = unsafe {
                libc::accept4(
                    listen_fd,
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                    libc::SOCK_NONBLOCK,
                )
            };

            if client < 0 {
                if would_block() {
                    return Ok(());
                }
                return Err(io::Error::last_os_error());
            }

            epoll_add(epfd, client, libc::EPOLLIN as u32)?;
            connections.insert(client, Connection::default());
        }
    }

    /// Drain readable bytes into the connection's output buffer.
    ///
    /// Returns `false` when the peer closed the connection.
    fn read_into(fd: i32, connections: &mut HashMap<i32, Connection>) -> io::Result<bool> {
        let mut buffer = [0u8; 4096];
        loop {
            // SAFETY: `buffer` is a valid writable region of `buffer.len()` bytes.
            let read =
                unsafe { libc::read(fd, buffer.as_mut_ptr() as *mut libc::c_void, buffer.len()) };

            if read == 0 {
                close_connection(fd, connections);
                return Ok(false);
            }
            if read < 0 {
                if would_block() {
                    break;
                }
                close_connection(fd, connections);
                return Err(io::Error::last_os_error());
            }

            if let Some(connection) = connections.get_mut(&fd) {
                connection.out.extend_from_slice(&buffer[..read as usize]);
            }
        }

        flush(fd, connections)?;
        Ok(true)
    }

    /// Write as much of the buffered reply as the socket accepts.
    fn flush(fd: i32, connections: &mut HashMap<i32, Connection>) -> io::Result<()> {
        let Some(connection) = connections.get_mut(&fd) else {
            return Ok(());
        };

        while connection.has_pending_output() {
            let remaining = connection.out.len() - connection.out_pos;
            // SAFETY: the slice is valid for `remaining` bytes.
            let written = unsafe {
                libc::write(
                    fd,
                    connection.out[connection.out_pos..].as_ptr() as *const libc::c_void,
                    remaining,
                )
            };

            if written < 0 {
                if would_block() {
                    // Keep the rest buffered; EPOLLOUT will drive the next attempt.
                    return Ok(());
                }
                return Err(io::Error::last_os_error());
            }
            connection.out_pos += written as usize;
        }

        connection.out.clear();
        connection.out_pos = 0;
        Ok(())
    }

    /// Ask for `EPOLLOUT` only while a reply is still buffered.
    fn update_interest(
        epfd: i32,
        fd: i32,
        connections: &mut HashMap<i32, Connection>,
    ) -> io::Result<()> {
        let pending = connections
            .get(&fd)
            .is_some_and(Connection::has_pending_output);
        let events = if pending {
            (libc::EPOLLIN | libc::EPOLLOUT) as u32
        } else {
            libc::EPOLLIN as u32
        };
        epoll_modify(epfd, fd, events)
    }

    fn close_connection(fd: i32, connections: &mut HashMap<i32, Connection>) {
        connections.remove(&fd);
        // SAFETY: `fd` is owned by us and open at this point.
        unsafe {
            libc::close(fd);
        }
    }

    fn epoll_add(epfd: i32, fd: i32, events: u32) -> io::Result<()> {
        let mut event = libc::epoll_event {
            events,
            u64: fd as u64,
        };
        // SAFETY: `event` outlives the call.
        if unsafe { libc::epoll_ctl(epfd, libc::EPOLL_CTL_ADD, fd, &mut event) } < 0 {
            Err(io::Error::last_os_error())
        } else {
            Ok(())
        }
    }

    fn epoll_modify(epfd: i32, fd: i32, events: u32) -> io::Result<()> {
        let mut event = libc::epoll_event {
            events,
            u64: fd as u64,
        };
        // SAFETY: `event` outlives the call.
        if unsafe { libc::epoll_ctl(epfd, libc::EPOLL_CTL_MOD, fd, &mut event) } < 0 {
            Err(io::Error::last_os_error())
        } else {
            Ok(())
        }
    }

    fn would_block() -> bool {
        matches!(
            io::Error::last_os_error().raw_os_error(),
            Some(libc::EAGAIN)
        )
    }
}

#[cfg(target_os = "linux")]
fn main() {
    use std::sync::atomic::AtomicBool;

    let port: u16 = std::env::args()
        .nth(1)
        .and_then(|argument| argument.parse().ok())
        .unwrap_or(9000);

    let (listen_fd, bound_port) = linux::bind_listener(port).expect("failed to bind");
    // SAFETY: epoll_create1 takes flags and returns an fd or -1.
    let epfd = unsafe { libc::epoll_create1(0) };
    assert!(epfd >= 0, "epoll_create1 failed");

    // A write to a peer that vanished raises SIGPIPE, which by default kills the
    // process. Servers ignore it and handle EPIPE from write instead.
    // SAFETY: installing SIG_IGN is a single-threaded startup action.
    unsafe {
        libc::signal(libc::SIGPIPE, libc::SIG_IGN);
    }

    println!("epoll echo server listening on 127.0.0.1:{bound_port} (Ctrl-C to stop)");

    let shutdown = AtomicBool::new(false);
    let result = linux::event_loop(epfd, listen_fd, &shutdown);
    // SAFETY: both fds are owned by this process.
    unsafe {
        libc::close(epfd);
        libc::close(listen_fd);
    }

    if let Err(error) = result {
        eprintln!("event loop error: {error}");
        std::process::exit(1);
    }
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("epoll_echo requires Linux; use kqueue or IOCP on this platform.");
}

#[cfg(all(test, target_os = "linux"))]
mod tests {
    use super::linux;
    use std::io::{Read, Write};
    use std::net::TcpStream;
    use std::sync::Arc;
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::thread;

    #[test]
    fn echoes_a_message_through_the_event_loop() {
        let (listen_fd, port) = linux::bind_listener(0).expect("bind");
        // SAFETY: epoll_create1 takes flags and returns an fd or -1.
        let epfd = unsafe { libc::epoll_create1(0) };
        assert!(epfd >= 0, "epoll_create1 failed");

        let shutdown = Arc::new(AtomicBool::new(false));
        let server_shutdown = Arc::clone(&shutdown);
        let server = thread::spawn(move || {
            let result = linux::event_loop(epfd, listen_fd, &server_shutdown);
            // SAFETY: the test owns both fds.
            unsafe {
                libc::close(epfd);
                libc::close(listen_fd);
            }
            result
        });

        let mut client = TcpStream::connect(("127.0.0.1", port)).expect("connect");
        client.write_all(b"epoll echo").expect("write");
        let mut echoed = [0u8; 10];
        client.read_exact(&mut echoed).expect("read echo");
        assert_eq!(&echoed, b"epoll echo");

        shutdown.store(true, Ordering::Relaxed);
        drop(client);
        let result = server.join().expect("server thread panicked");
        assert!(result.is_ok(), "event loop returned {result:?}");
    }
}
