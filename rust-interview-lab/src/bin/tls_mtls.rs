//! TLS with rustls: a client that checks the server's certificate, the errors
//! it reports when the check fails, and mutual TLS, where the server checks a
//! certificate from the client as well.
//!
//! The certificates are made at startup with rcgen: one certificate authority,
//! a server certificate for "localhost", and a client certificate for a
//! service called "billing". Nothing secret is stored on disk.
//!
//! Run with: cargo run --bin tls_mtls

use std::{
    io::{self, Read, Write},
    net::{TcpListener, TcpStream},
    sync::{Arc, Mutex},
    thread,
};

use rcgen::{BasicConstraints, CertificateParams, DnType, IsCa, KeyPair};
use rustls::{
    ClientConfig,
    ClientConnection,
    RootCertStore,
    ServerConfig,
    ServerConnection,
    StreamOwned,
    crypto::{CryptoProvider, ring},
    pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer, ServerName},
    server::WebPkiClientVerifier,
};

type Error = Box<dyn std::error::Error + Send + Sync>;

/// A certificate and the private key that goes with it.
struct Identity {
    cert: CertificateDer<'static>,
    key: PrivatePkcs8KeyDer<'static>,
}

impl Identity {
    fn key(&self) -> PrivateKeyDer<'static> {
        PrivateKeyDer::Pkcs8(self.key.clone_key())
    }
}

/// A certificate authority, and certificates it signed for a server and a client.
struct Pki {
    ca: CertificateDer<'static>,
    server: Identity,
    client: Identity,
}

impl Pki {
    fn new() -> Result<Self, Error> {
        let ca_key = KeyPair::generate()?;
        let mut ca_params = CertificateParams::new(Vec::<String>::new())?;
        ca_params.is_ca = IsCa::Ca(BasicConstraints::Unconstrained);
        ca_params
            .distinguished_name
            .push(DnType::CommonName, "lab CA");
        let ca = ca_params.self_signed(&ca_key)?;

        let issue = |name: &str| -> Result<Identity, Error> {
            let key = KeyPair::generate()?;
            let mut params = CertificateParams::new(vec![name.to_string()])?;
            params
                .distinguished_name
                .push(DnType::CommonName, name);
            let cert = params.signed_by(&key, &ca, &ca_key)?;
            Ok(Identity {
                cert: cert.der().clone(),
                key: PrivatePkcs8KeyDer::from(key.serialize_der()),
            })
        };
        let server = issue("localhost")?;
        let client = issue("billing")?;
        Ok(Self {
            ca: ca.der().clone(),
            server,
            client,
        })
    }

    /// A trust store holding only this CA.
    fn roots(&self) -> Result<RootCertStore, Error> {
        let mut roots = RootCertStore::empty();
        roots.add(self.ca.clone())?;
        Ok(roots)
    }
}

/// The ring crypto provider, named explicitly so the program does not depend
/// on which provider other crates enable.
fn provider() -> Arc<CryptoProvider> {
    Arc::new(ring::default_provider())
}

/// A TCP stream that keeps a copy of every byte it sends.
struct Tap {
    stream: TcpStream,
    sent: Arc<Mutex<Vec<u8>>>,
}

impl Read for Tap {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        self.stream.read(buffer)
    }
}

impl Write for Tap {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        let written = self.stream.write(buffer)?;
        self.sent
            .lock()
            .expect("tap lock")
            .extend_from_slice(&buffer[..written]);
        Ok(written)
    }

    fn flush(&mut self) -> io::Result<()> {
        self.stream.flush()
    }
}

/// The TLS records in a byte stream, as (content type, length) pairs.
fn records(mut bytes: &[u8]) -> Vec<(&'static str, usize)> {
    let mut found = Vec::new();
    while let [kind, _, _, high, low, rest @ ..] = bytes {
        let length = usize::from(*high) << 8 | usize::from(*low);
        let name = match kind {
            20 => "change_cipher_spec",
            21 => "alert",
            22 => "handshake",
            23 => "application_data",
            _ => "unknown",
        };
        found.push((name, length));
        bytes = rest.get(length..).unwrap_or_default();
    }
    found
}

/// Accept one connection, and answer one message in capitals. Returns what
/// the server learned about the client, or the error that ended the handshake.
fn serve_once(listener: TcpListener, config: Arc<ServerConfig>) -> thread::JoinHandle<String> {
    thread::spawn(move || {
        let outcome = || -> Result<String, Error> {
            let (stream, _) = listener.accept()?;
            let mut tls = StreamOwned::new(ServerConnection::new(config)?, stream);
            let mut message = [0; 64];
            let read = tls.read(&mut message)?;
            tls.write_all(&message[..read].to_ascii_uppercase())?;
            tls.conn.send_close_notify();
            tls.flush()?;
            Ok(match tls.conn.peer_certificates() {
                Some(chain) => format!("client presented {} verified certificate", chain.len()),
                None => "client presented no certificate".to_string(),
            })
        };
        outcome().unwrap_or_else(|error| format!("handshake failed: {error}"))
    })
}

/// What one client connection saw.
struct Session {
    version: String,
    suite: String,
    reply: String,
    sent: Vec<u8>,
}

/// Connect to `listener` with `config`, expecting the server to be `name`,
/// send one message, and read the reply.
fn connect(listener: &TcpListener, config: ClientConfig, name: &str) -> Result<Session, Error> {
    let sent = Arc::new(Mutex::new(Vec::new()));
    let tap = Tap {
        stream: TcpStream::connect(listener.local_addr()?)?,
        sent: Arc::clone(&sent),
    };
    let name = ServerName::try_from(name.to_string())?;
    let mut tls = StreamOwned::new(ClientConnection::new(Arc::new(config), name)?, tap);

    tls.write_all(b"hello over tls")?;
    let mut reply = String::new();
    tls.read_to_string(&mut reply)?;

    Ok(Session {
        version: format!(
            "{:?}",
            tls.conn
                .protocol_version()
                .ok_or("no version")?
        ),
        suite: format!(
            "{:?}",
            tls.conn
                .negotiated_cipher_suite()
                .ok_or("no suite")?
                .suite()
        ),
        reply,
        sent: sent.lock().expect("tap lock").clone(),
    })
}

/// Run one client against one server, and print what each side reported.
fn run(server: ServerConfig, client: ClientConfig, name: &str) -> Result<(), Error> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let server = serve_once(listener.try_clone()?, Arc::new(server));
    match connect(&listener, client, name) {
        Ok(session) => {
            println!(
                "  client: {} {}, reply {:?}",
                session.version, session.suite, session.reply
            );
            println!("  client sent records: {:?}", records(&session.sent));
            let visible = session
                .sent
                .windows(5)
                .any(|window| window == b"hello");
            println!("  \"hello\" readable on the wire: {visible}");
        }
        Err(error) => println!("  client: {error}"),
    }
    println!("  server: {}", server.join().expect("server thread"));
    Ok(())
}

fn main() -> Result<(), Error> {
    let pki = Pki::new()?;
    let server_only = || -> Result<ServerConfig, Error> {
        Ok(ServerConfig::builder_with_provider(provider())
            .with_safe_default_protocol_versions()?
            .with_no_client_auth()
            .with_single_cert(vec![pki.server.cert.clone()], pki.server.key())?)
    };
    let client_trusting = |roots: RootCertStore| -> Result<ClientConfig, Error> {
        Ok(ClientConfig::builder_with_provider(provider())
            .with_safe_default_protocol_versions()?
            .with_root_certificates(roots)
            .with_no_client_auth())
    };

    println!("1. The client checks the server's certificate");
    run(server_only()?, client_trusting(pki.roots()?)?, "localhost")?;

    println!("\n2. The client expects a different name");
    run(
        server_only()?,
        client_trusting(pki.roots()?)?,
        "billing.example",
    )?;

    println!("\n3. The client does not trust the CA");
    run(
        server_only()?,
        client_trusting(RootCertStore::empty())?,
        "localhost",
    )?;

    let verifier =
        WebPkiClientVerifier::builder_with_provider(Arc::new(pki.roots()?), provider()).build()?;
    let mutual = || -> Result<ServerConfig, Error> {
        Ok(ServerConfig::builder_with_provider(provider())
            .with_safe_default_protocol_versions()?
            .with_client_cert_verifier(verifier.clone())
            .with_single_cert(vec![pki.server.cert.clone()], pki.server.key())?)
    };

    println!("\n4. Mutual TLS, client without a certificate");
    run(mutual()?, client_trusting(pki.roots()?)?, "localhost")?;

    println!("\n5. Mutual TLS, client with the billing certificate");
    let client = ClientConfig::builder_with_provider(provider())
        .with_safe_default_protocol_versions()?
        .with_root_certificates(pki.roots()?)
        .with_client_auth_cert(vec![pki.client.cert.clone()], pki.client.key())?;
    run(mutual()?, client, "localhost")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_are_split_by_their_length_field() {
        let bytes = [22, 3, 1, 0, 2, 0xAA, 0xBB, 23, 3, 3, 0, 1, 0xCC];
        assert_eq!(records(&bytes), [("handshake", 2), ("application_data", 1)]);
    }

    #[test]
    fn a_trusted_server_answers() {
        let pki = Pki::new().expect("pki");
        let server = ServerConfig::builder_with_provider(provider())
            .with_safe_default_protocol_versions()
            .unwrap()
            .with_no_client_auth()
            .with_single_cert(vec![pki.server.cert.clone()], pki.server.key())
            .unwrap();
        let client = ClientConfig::builder_with_provider(provider())
            .with_safe_default_protocol_versions()
            .unwrap()
            .with_root_certificates(pki.roots().unwrap())
            .with_no_client_auth();
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let handle = serve_once(listener.try_clone().unwrap(), Arc::new(server));
        let session = connect(&listener, client, "localhost").expect("session");
        assert_eq!(session.reply, "HELLO OVER TLS");
        handle.join().unwrap();
    }
}
