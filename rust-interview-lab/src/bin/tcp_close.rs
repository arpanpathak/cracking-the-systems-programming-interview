//! Closing a TCP connection: the states each side passes through, `TIME_WAIT`
//! on the side that closes first, the `CLOSE_WAIT` sockets a server keeps when
//! it never closes, and the reset that replaces `FIN` when data goes unread.
//!
//! Linux only: the states are read from /proc/net/tcp.
//! Run with: cargo run --bin tcp_close

#[cfg(target_os = "linux")]
mod linux {
    use std::{
        collections::BTreeMap,
        fs,
        io::{self, Read, Write},
        mem,
        net::{SocketAddr, SocketAddrV4, TcpListener, TcpStream},
        os::fd::{FromRawFd, OwnedFd},
        thread,
        time::Duration,
    };

    /// Long enough for loopback segments to be sent, received, and acknowledged.
    pub const SETTLE: Duration = Duration::from_millis(50);

    /// One line of /proc/net/tcp: local port, remote port, and state.
    struct Entry {
        local: u16,
        remote: u16,
        state: &'static str,
    }

    /// The name of a TCP state, from the number Linux prints for it.
    fn state_name(code: u8) -> &'static str {
        match code {
            0x01 => "ESTABLISHED",
            0x02 => "SYN_SENT",
            0x03 => "SYN_RECV",
            0x04 => "FIN_WAIT1",
            0x05 => "FIN_WAIT2",
            0x06 => "TIME_WAIT",
            0x07 => "CLOSE",
            0x08 => "CLOSE_WAIT",
            0x09 => "LAST_ACK",
            0x0A => "LISTEN",
            0x0B => "CLOSING",
            _ => "UNKNOWN",
        }
    }

    /// The port in an address written as `0100007F:1F90`.
    fn port_of(field: &str) -> Option<u16> {
        let (_, port) = field.split_once(':')?;
        u16::from_str_radix(port, 16).ok()
    }

    /// Every IPv4 TCP socket the kernel knows about.
    fn entries() -> io::Result<Vec<Entry>> {
        let table = fs::read_to_string("/proc/net/tcp")?;
        Ok(table
            .lines()
            .skip(1)
            .filter_map(|line| {
                let fields: Vec<&str> = line.split_whitespace().collect();
                Some(Entry {
                    local: port_of(fields.get(1)?)?,
                    remote: port_of(fields.get(2)?)?,
                    state: state_name(u8::from_str_radix(fields.get(3)?, 16).ok()?),
                })
            })
            .collect())
    }

    /// The state of the socket whose local and remote ports are `local` and
    /// `remote`, or "gone" if the kernel has forgotten it.
    pub fn state(local: SocketAddr, remote: SocketAddr) -> io::Result<&'static str> {
        Ok(entries()?
            .into_iter()
            .find(|entry| entry.local == local.port() && entry.remote == remote.port())
            .map_or("gone", |entry| entry.state))
    }

    /// How many sockets on the server's `port` are in each state, counting
    /// both the server's side and the clients' side of each connection.
    pub fn census(port: u16) -> io::Result<BTreeMap<&'static str, usize>> {
        let mut counts = BTreeMap::new();
        for entry in entries()? {
            if entry.state != "LISTEN" && (entry.local == port || entry.remote == port) {
                *counts.entry(entry.state).or_insert(0) += 1;
            }
        }
        Ok(counts)
    }

    /// A connected pair over loopback: (client, server's accepted socket).
    pub fn connected(listener: &TcpListener) -> io::Result<(TcpStream, TcpStream)> {
        let client = TcpStream::connect(listener.local_addr()?)?;
        let (server, _) = listener.accept()?;
        Ok((client, server))
    }

    /// Bind a listening socket to `port` on loopback with raw calls, setting
    /// `SO_REUSEADDR` only if `reuse` is true. `TcpListener::bind` always sets it.
    pub fn bind_raw(port: u16, reuse: bool) -> io::Result<OwnedFd> {
        // SAFETY: socket takes no pointers, and the result is checked.
        let fd = unsafe { libc::socket(libc::AF_INET, libc::SOCK_STREAM | libc::SOCK_CLOEXEC, 0) };
        if fd < 0 {
            return Err(io::Error::last_os_error());
        }
        // SAFETY: the descriptor was just created, and nothing else owns it.
        let socket = unsafe { OwnedFd::from_raw_fd(fd) };

        let enable: libc::c_int = 1;
        let address = SocketAddrV4::new([127, 0, 0, 1].into(), port);
        // SAFETY: sockaddr_in is plain data, and all zeros is a valid value.
        let mut raw: libc::sockaddr_in = unsafe { mem::zeroed() };
        raw.sin_family = libc::AF_INET as libc::sa_family_t;
        raw.sin_port = address.port().to_be();
        raw.sin_addr.s_addr = u32::from_ne_bytes(address.ip().octets());

        // SAFETY: the option value and the address are valid for the lengths
        // passed, and outlive both calls.
        let result = unsafe {
            if reuse {
                libc::setsockopt(
                    fd,
                    libc::SOL_SOCKET,
                    libc::SO_REUSEADDR,
                    (&enable as *const libc::c_int).cast(),
                    mem::size_of::<libc::c_int>() as libc::socklen_t,
                );
            }
            libc::bind(
                fd,
                (&raw as *const libc::sockaddr_in).cast(),
                mem::size_of::<libc::sockaddr_in>() as libc::socklen_t,
            )
        };
        if result < 0 {
            return Err(io::Error::last_os_error());
        }
        Ok(socket)
    }

    /// A server that accepts `clients` connections and never closes them,
    /// while each client connects and closes at once. Returns the listener's
    /// port and the accepted sockets, still open.
    pub fn leaky_server(clients: usize) -> io::Result<(u16, Vec<TcpStream>)> {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let port = listener.local_addr()?.port();
        let mut kept = Vec::new();
        for _ in 0..clients {
            let (client, server) = connected(&listener)?;
            drop(client);
            kept.push(server);
        }
        thread::sleep(SETTLE);
        Ok((port, kept))
    }

    /// The client writes bytes the server never reads, then the server closes.
    /// Returns what the client's next read reports.
    pub fn close_with_unread_data() -> io::Result<io::Result<usize>> {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let (mut client, server) = connected(&listener)?;
        client.write_all(b"a request the server never reads")?;
        thread::sleep(SETTLE);
        drop(server);
        thread::sleep(SETTLE);
        Ok(client.read(&mut [0; 64]))
    }
}

#[cfg(target_os = "linux")]
fn main() -> std::io::Result<()> {
    use std::{
        io::{Read, Write},
        net::{Shutdown, TcpListener},
        thread,
    };

    use linux::{SETTLE, census, connected, state};

    println!("1. An orderly close, client first, with a half-close\n");
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let (mut client, mut server) = connected(&listener)?;
    let (c, s) = (client.local_addr()?, server.local_addr()?);
    let show = |step: &str| -> std::io::Result<()> {
        thread::sleep(SETTLE);
        println!("  {step:<38} {:<12} {}", state(c, s)?, state(s, c)?);
        Ok(())
    };
    println!("  {:<38} {:<12} {}", "step", "client", "server");
    show("connected")?;
    client.shutdown(Shutdown::Write)?;
    show("client shutdown(Write): FIN sent")?;
    let mut request = Vec::new();
    server.read_to_end(&mut request)?;
    server.write_all(b"reply")?;
    show("server read to end, wrote a reply")?;
    drop(server);
    show("server dropped its socket: FIN sent")?;
    let mut reply = String::new();
    client.read_to_string(&mut reply)?;
    drop(client);
    show("client read the reply, dropped")?;

    println!("\n2. A server that never closes what clients closed\n");
    let (port, kept) = linux::leaky_server(5)?;
    println!("  while the server keeps 5 sockets: {:?}", census(port)?);
    drop(kept);
    thread::sleep(SETTLE);
    println!("  after the server drops them:      {:?}", census(port)?);

    println!("\n3. TIME_WAIT on the server's port, and binding it again\n");
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let port = listener.local_addr()?.port();
    let (client, server) = connected(&listener)?;
    drop(server);
    thread::sleep(SETTLE);
    drop(client);
    drop(listener);
    thread::sleep(SETTLE);
    println!(
        "  server closed first, then the client: {:?}",
        census(port)?
    );
    for reuse in [false, true] {
        let outcome = match linux::bind_raw(port, reuse) {
            Ok(_) => "bound".to_string(),
            Err(error) => error.to_string(),
        };
        println!("  bind port again, SO_REUSEADDR {reuse:<5}: {outcome}");
    }

    println!("\n4. Closing with unread data\n");
    match linux::close_with_unread_data()? {
        Ok(read) => println!("  client read returned {read}"),
        Err(error) => println!("  client read failed: {error}"),
    }
    Ok(())
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("tcp_close reads TCP states from Linux's /proc/net/tcp; run it on Linux");
}

#[cfg(all(test, target_os = "linux"))]
mod tests {
    use std::{io::ErrorKind, net::TcpListener, thread};

    use super::linux::*;

    #[test]
    fn the_side_that_closes_first_holds_time_wait() {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind");
        let (client, server) = connected(&listener).expect("connect");
        let (c, s) = (client.local_addr().unwrap(), server.local_addr().unwrap());
        drop(server);
        thread::sleep(SETTLE);
        drop(client);
        thread::sleep(SETTLE);
        assert_eq!(state(s, c).expect("state"), "TIME_WAIT");
        assert_eq!(state(c, s).expect("state"), "gone");
    }

    #[test]
    fn a_server_that_never_closes_holds_close_wait() {
        let (port, _kept) = leaky_server(3).expect("server");
        assert_eq!(census(port).expect("census").get("CLOSE_WAIT"), Some(&3));
    }

    #[test]
    fn unread_data_turns_close_into_reset() {
        let error = close_with_unread_data()
            .expect("setup")
            .expect_err("read should fail");
        assert_eq!(error.kind(), ErrorKind::ConnectionReset);
    }
}
