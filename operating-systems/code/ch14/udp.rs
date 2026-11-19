// ch14/udp.rs: the same datagram round trip with std::net::UdpSocket.
use std::net::UdpSocket;

fn main() -> std::io::Result<()> {
    let s = UdpSocket::bind("127.0.0.1:45681")?;

    let msg = b"datagram";
    s.send_to(msg, "127.0.0.1:45681")?;

    let mut buf = [0u8; 64];
    let (n, from) = s.recv_from(&mut buf)?;

    println!(
        "sent {} bytes, received {n} bytes from {from}: \"{}\"",
        msg.len(),
        String::from_utf8_lossy(&buf[..n])
    );
    Ok(())
}
