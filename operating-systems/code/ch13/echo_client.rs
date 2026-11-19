// ch13/echo_client.rs: connect, send three messages, verify the echoes.
use std::io::{Read, Write};
use std::net::TcpStream;

fn main() {
    let mut stream = TcpStream::connect("127.0.0.1:45679").expect("connect failed");

    for msg in ["one", "two", "three"] {
        stream.write_all(msg.as_bytes()).expect("write failed");
        let mut buf = [0_u8; 64];
        let n = stream.read(&mut buf).expect("read failed");
        let got = std::str::from_utf8(&buf[..n]).unwrap_or("");
        let status = if got == msg { "ok" } else { "MISMATCH" };
        println!("sent \"{msg}\", got \"{got}\" ({status})");
    }
}
