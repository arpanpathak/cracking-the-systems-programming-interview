// ch13/thread_echo.rs: a thread-per-connection echo server plus its client,
// both in one process, written with the Rust standard library only.
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

fn handle(mut s: TcpStream, id: usize) {
    let mut buf = [0u8; 256];

    loop {
        match s.read(&mut buf) {
            Ok(0) => break, // peer closed
            Ok(n) => {
                if let Err(e) = s.write_all(&buf[..n]) {
                    eprintln!("thread {id}: {e}");
                    break;
                }
                println!("thread {id} echoed {n} bytes");
            }
            Err(e) => {
                eprintln!("thread {id}: {e}");
                break;
            }
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let listener = TcpListener::bind("127.0.0.1:45679")?;
    println!("listening on 127.0.0.1:45679");

    let server = thread::spawn(move || {
        let mut id = 0;
        for stream in listener.incoming() {
            match stream {
                Ok(s) => {
                    id += 1;
                    println!("accepted client {id}");
                    thread::spawn(move || handle(s, id));
                }
                Err(e) => {
                    eprintln!("accept: {e}");
                    break;
                }
            }

            if id >= 2 {
                break;
            }
        }
    });

    for c in 0..2 {
        let mut s = TcpStream::connect("127.0.0.1:45679")?;

        for m in ["alpha", "beta", "gamma"] {
            s.write_all(m.as_bytes())?;
            let mut buf = [0u8; 64];
            let n = s.read(&mut buf)?;
            let got = String::from_utf8_lossy(&buf[..n]);
            println!("client {c} sent \"{m}\", got \"{got}\" (ok={})", got == m);
        }
    }

    server.join().map_err(|_| "server thread panicked")?;
    println!("done");
    Ok(())
}
