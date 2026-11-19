// ch14/to_socket_addrs.rs: the Rust equivalent of getaddrinfo.
use std::net::ToSocketAddrs;

fn main() {
    for (i, addr) in ("localhost", 45682).to_socket_addrs().unwrap().enumerate() {
        println!("[{i}] {addr}");
    }
}
