// ch14/to_socket_addrs.rs: the Rust equivalent of getaddrinfo.
use std::net::ToSocketAddrs;

fn main() -> std::io::Result<()> {
    for (i, addr) in ("localhost", 45682).to_socket_addrs()?.enumerate() {
        println!("[{i}] {addr}");
    }
    Ok(())
}
