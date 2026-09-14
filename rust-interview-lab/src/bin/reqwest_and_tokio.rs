use std::{collections::HashMap, sync::Mutex, time::Duration};
use reqwest::{Client, Method, StatusCode};
use serde_json::Value;

type Error = Box<dyn std::error::Error + Send + Sync>;

const RETRY: [StatusCode; 5] = [
    StatusCode::TOO_MANY_REQUESTS,
    StatusCode::INTERNAL_SERVER_ERROR,
    StatusCode::BAD_GATEWAY,
    StatusCode::SERVICE_UNAVAILABLE,
    StatusCode::GATEWAY_TIMEOUT,
];

struct Config {
    base: String,
    max_attempts: u32,
    base_delay: Duration,
    max_delay: Duration,
    timeout: Duration,
}

struct Api {
    http: Client,
    cache: Mutex<HashMap<String, String>>,
    cfg: Config,
}

impl Api {
    fn new(cfg: Config) -> Result<Self, Error> {
        Ok(Self {
            http: Client::builder().timeout(cfg.timeout).build()?,
            cache: Mutex::new(HashMap::new()),
            cfg,
        })
    }

    fn cached(&self, key: &str) -> Option<String> {
        self.cache
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .get(key)
            .cloned()
    }

    fn store(&self, key: &str, text: &str) {
        self.cache
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .insert(key.into(), text.into());
    }

    async fn call(
        &self,
        key: &str,
        method: Method,
        path: &str,
        body: Option<&Value>,
    ) -> Result<String, Error> {
        match self.cached(key) {
            Some(hit) => return Ok(hit),
            None => {}
        }

        let url = format!("{}{}", self.cfg.base, path);
        let mut delay = self.cfg.base_delay;
        let mut attempt = 0;

        loop {
            attempt += 1;

            let req = self
                .http
                .request(method.clone(), &url)
                .header("Idempotency-Key", key)
                .header("Accept", "application/json");
            let req = match body {
                Some(b) => req.json(b),
                None => req,
            };

            let resp = req.send().await?;
            let status = resp.status();
            let text = resp.text().await?;

            match status {
                s if s.is_success() => {
                    self.store(key, &text);
                    return Ok(text);
                }
                s if RETRY.contains(&s) && attempt < self.cfg.max_attempts => {
                    tokio::time::sleep(delay).await;
                    delay = (delay * 2).min(self.cfg.max_delay);
                }
                s => return Err(format!("HTTP {s} after {attempt} attempts: {text}").into()),
            }
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Error> {
    let api = Api::new(Config {
        base: "https://httpbin.org".into(),
        max_attempts: 3,
        base_delay: Duration::from_millis(100),
        max_delay: Duration::from_secs(5),
        timeout: Duration::from_secs(15),
    })?;

    let body = serde_json::json!({ "name": "demo" });
    let out = api
        .call("create-demo-001", Method::POST, "/post", Some(&body))
        .await?;
    println!("created:\n{out}");
    Ok(())
}