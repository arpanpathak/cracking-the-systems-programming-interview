//! TCP echo server: the canonical socket exercise.
//!
//! Demonstrates the server side of the TCP lifecycle: `bind` -> `listen` ->
//! `accept` -> read/write loop -> peer `close` (a `read` of 0). It uses a
//! thread-per-connection model, which is the right default for bounded concurrency
//! and blocking handlers; the event-loop alternative is `src/bin/epoll_echo.rs`.
//!
//! `TCP_NODELAY` is set because an echo server must not sit on Nagle's algorithm
//! waiting to coalesce a reply that will never be followed by more data.
//!
//! ```bash
//! cargo run --bin tcp_echo_server            # binds 127.0.0.1:0, prints the port
//! cargo run --bin tcp_echo_server 0.0.0.0:9000
//! ```

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

/// Accept connections forever, handling each on its own thread.
pub fn serve(listener: TcpListener) {
    for incoming in listener.incoming() {
        match incoming {
            Ok(stream) => {
                thread::spawn(move || {
                    if let Err(error) = handle_connection(stream) {
                        eprintln!("connection error: {error}");
                    }
                });
            }
            Err(error) => eprintln!("accept error: {error}"),
        }
    }
}

/// Echo every byte back until the peer closes the connection.
fn handle_connection(mut stream: TcpStream) -> std::io::Result<()> {
    stream.set_nodelay(true)?;
    if let Ok(peer) = stream.peer_addr() {
        println!("connection from {peer}");
    }

    let mut buffer = [0u8; 4096];
    loop {
        let read = stream.read(&mut buffer)?;
        if read == 0 {
            // A zero-byte read is the peer's FIN: an orderly close.
            return Ok(());
        }
        stream.write_all(&buffer[..read])?;
    }
}

fn main() {
    let address = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "127.0.0.1:0".to_string());

    let listener = TcpListener::bind(&address).expect("failed to bind");
    let local = listener.local_addr().expect("failed to read local address");
    println!("tcp echo server listening on {local}");

    serve(listener);
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::Shutdown;

    #[test]
    fn echoes_bytes_until_the_client_closes() {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral port");
        let address = listener.local_addr().expect("local address");

        // Accept exactly one connection, echo it, then return so the test can join.
        let server = thread::spawn(move || {
            let (stream, _) = listener.accept().expect("accept one connection");
            handle_connection(stream).expect("echo");
        });

        let mut client = TcpStream::connect(address).expect("connect");
        client.write_all(b"hello gpu").expect("write");
        client.shutdown(Shutdown::Write).expect("half close");

        let mut echoed = Vec::new();
        client.read_to_end(&mut echoed).expect("read echo");

        server.join().expect("server thread panicked");
        assert_eq!(echoed, b"hello gpu");
    }
}
