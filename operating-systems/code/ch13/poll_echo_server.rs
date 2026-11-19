// ch13/poll_echo_server.rs: one thread, several clients, poll(2) in Rust.
extern crate libc;

use std::io::{Read, Write};
use std::net::TcpListener;
use std::os::fd::AsRawFd;

fn main() {
    let listener = TcpListener::bind("127.0.0.1:45679").expect("bind failed");
    println!("listening on 127.0.0.1:45679");

    let listen_fd = listener.as_raw_fd();
    let mut fds = vec![libc::pollfd {
        fd: listen_fd,
        events: libc::POLLIN,
        revents: 0,
    }];
    let mut streams = Vec::new();
    let mut clients_served = 0;

    while clients_served < 2 {
        // SAFETY: `fds` is a valid contiguous `Vec<libc::pollfd>` whose descriptors
        // are owned by `listener` and `streams` for the duration of the loop.
        let rc = unsafe { libc::poll(fds.as_mut_ptr(), fds.len() as libc::nfds_t, 1000) };
        assert!(rc >= 0, "poll failed");

        if (fds[0].revents & libc::POLLIN) != 0 {
            let (stream, _) = listener.accept().expect("accept failed");
            let cfd = stream.as_raw_fd();
            println!("accepted fd {cfd}");
            fds.push(libc::pollfd {
                fd: cfd,
                events: libc::POLLIN,
                revents: 0,
            });
            streams.push(stream);
        }

        let mut i = 0;
        while i < streams.len() {
            if (fds[i + 1].revents & libc::POLLIN) != 0 {
                let cfd = fds[i + 1].fd;
                let mut buf = [0_u8; 256];
                let n = streams[i].read(&mut buf).unwrap_or(0);
                if n == 0 {
                    println!("client fd {cfd} closed");
                    streams.remove(i);
                    fds.remove(i + 1);
                    clients_served += 1;
                    continue;
                }
                println!("echoing {n} bytes to fd {cfd}");
                streams[i].write_all(&buf[..n]).expect("write failed");
            }
            i += 1;
        }
    }

    println!("served 2 clients, exiting");
}
