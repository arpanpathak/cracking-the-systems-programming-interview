use std::collections::HashMap;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::sync::Mutex;
use std::time::Duration;

type RuntimeError = Box<dyn std::error::Error>;

enum RequestType {
    GET    { path: String, headers: Vec<(String, String)> },
    OPTION { path: String, headers: Vec<(String, String)> },
    POST   { path: String, headers: Vec<(String, String)>, body: String },
    PUT    { path: String, headers: Vec<(String, String)>, body: String },
}

struct IdemCache {
    store: Mutex<HashMap<String, String>>,
}

impl IdemCache {
    fn new() -> Self {
        Self { store: Mutex::new(HashMap::new()) }
    }

    fn get_or_insert<F>(&self, key: &str, f: F) -> Result<String, RuntimeError>
    where
        F: FnOnce() -> Result<String, RuntimeError>,
    {
        let mut store = self.store.lock().map_err(|_| "lock poisoned")?;
        if let Some(v) = store.get(key) {
            return Ok(v.clone());
        }
        let v = f()?;
        store.insert(key.to_string(), v.clone());
        Ok(v)
    }
}

struct RetryPolicy {
    max_attempts: u32,
    base_delay: Duration,
    max_delay: Duration,
}

impl RetryPolicy {
    fn new() -> Self {
        Self {
            max_attempts: 3,
            base_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(5),
        }
    }

    fn execute<F, T>(&self, mut f: F) -> Result<T, RuntimeError>
    where
        F: FnMut() -> Result<T, RuntimeError>,
    {
        let mut attempt = 0;
        loop {
            attempt += 1;
            match f() {
                Ok(v) => return Ok(v),
                Err(e) if attempt >= self.max_attempts => return Err(e),
                Err(_) => {
                    let delay = (self.base_delay * 2u32.pow(attempt - 1)).min(self.max_delay);
                    std::thread::sleep(delay);
                }
            }
        }
    }
}

/// -- Build a HTTP client with those strategies

struct HttpClient {
    host: String,
    port: u16,
    cache: IdemCache,
    retry: RetryPolicy,
}

impl HttpClient {
    fn new(host: &str, port: u16) -> Self {
        Self {
            host: host.to_string(),
            port,
            cache: IdemCache::new(),
            retry: RetryPolicy::new(),
        }
    }

    fn execute(&self, key: &str, req: &RequestType) -> Result<String, RuntimeError> {
        self.cache.get_or_insert(key, || self.retry.execute(|| self.send(req)))
    }

    fn send(&self, req: &RequestType) -> Result<String, RuntimeError> {
        let (method, path, headers, body) = match req {
            RequestType::GET    { path, headers }       => ("GET",     path, headers, None),
            RequestType::OPTION { path, headers }       => ("OPTIONS", path, headers, None),
            RequestType::POST   { path, headers, body } => ("POST",    path, headers, Some(body)),
            RequestType::PUT    { path, headers, body } => ("PUT",     path, headers, Some(body)),
        };

        let mut raw = format!(
            "{method} {path} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n",
            self.host
        );
        for (k, v) in headers { raw += &format!("{k}: {v}\r\n"); }
        if let Some(b) = body { raw += &format!("Content-Length: {}\r\n", b.len()); }
        raw += "\r\n";
        if let Some(b) = body { raw += b; }

        let mut stream = TcpStream::connect((self.host.as_str(), self.port))?;
        stream.write_all(raw.as_bytes())?;
        let mut resp = String::new();
        stream.read_to_string(&mut resp)?;
        Ok(resp.split_once("\r\n\r\n").map(|(_, b)| b).unwrap_or("").to_string())
    }
}

// --- The actual REST call ---

fn create_item(client: &HttpClient, item_name: &str) -> Result<String, RuntimeError> {
    client.execute("create-demo-001", &RequestType::POST {
        path: "/post".into(),
        headers: vec![
            ("Content-Type".into(), "application/json".into()),
            ("Accept".into(), "application/json".into()),
        ],
        body: format!(r#"{{"name":"{item_name}"}}"#),
    })
}

fn main() -> Result<(), RuntimeError> {
    let client = HttpClient::new("httpbin.org", 80);
    println!("created:\n{}", create_item(&client, "demo")?);
    Ok(())
}