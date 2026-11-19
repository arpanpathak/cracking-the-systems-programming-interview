// ch14/udp.rs: the same datagram round trip with std::net::UdpSocket.
use std::net::UdpSocket;

fn main() {
    let s = UdpSocket::bind("127.0.0.1:45681").unwrap();

    let msg = b"datagram";
    s.send_to(msg, "127.0.0.1:45681").unwrap();

    let mut buf = [0u8; 64];
    let (n, from) = s.recv_from(&mut buf).unwrap();

    println!(
        "sent {} bytes, received {n} bytes from {from}: \"{}\"",
        msg.len(),
        String::from_utf8_lossy(&buf[..n])
    );
}
