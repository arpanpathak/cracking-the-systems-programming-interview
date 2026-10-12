//! A small command-line client for a GPU cluster, written to build and behave
//! the same on Linux, macOS, and Windows.
//!
//! ```text
//! gpuctl nodes [-o table|json]   list the cluster's nodes and their GPUs
//! gpuctl config                  print where gpuctl looks for its files
//! gpuctl version                 print the version and the platform
//! ```
//!
//! Data goes to standard output and messages to standard error. The exit
//! status is 0 on success, 1 when a command fails, and 2 when the command line
//! is wrong.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p gpuctl -- nodes
//! ```

use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

use k8s_openapi::api::core::v1::Node;
use kube::{Api, Client, api::ListParams};
use serde::Serialize;

// ANCHOR: exit
/// The exit status for a command line that is wrong. A script that calls
/// gpuctl tells a failed command from a mistyped one by the status alone:
/// success is 0 and failure is 1, which `ExitCode` already names.
const EXIT_USAGE: u8 = 2;

const USAGE: &str = "usage:
  gpuctl nodes [-o table|json]
  gpuctl config
  gpuctl version
";
// ANCHOR_END: exit

// ANCHOR: paths
/// Returns the path of gpuctl's own configuration file. The directory is the
/// one each operating system sets aside for a user's settings.
fn config_file() -> Option<PathBuf> {
    let dir = if cfg!(windows) {
        PathBuf::from(env::var_os("AppData")?)
    } else if cfg!(target_os = "macos") {
        env::home_dir()?.join("Library").join("Application Support")
    } else {
        match env::var_os("XDG_CONFIG_HOME") {
            Some(dir) if !dir.is_empty() => PathBuf::from(dir),
            _ => env::home_dir()?.join(".config"),
        }
    };

    Some(dir.join("gpuctl").join("config.toml"))
}

/// Returns the file that names the cluster and the credentials: the
/// KUBECONFIG environment variable if it is set, and .kube/config in the
/// user's home directory otherwise.
fn kubeconfig() -> Option<PathBuf> {
    match env::var_os("KUBECONFIG") {
        Some(path) if !path.is_empty() => Some(PathBuf::from(path)),
        _ => Some(env::home_dir()?.join(".kube").join("config")),
    }
}
// ANCHOR_END: paths

// ANCHOR: nodes
/// One row of "gpuctl nodes".
#[derive(Serialize)]
struct NodeInfo {
    name: String,
    gpus: i64,
    arch: String,
    os: String,
    kubelet: String,
}

/// Asks the API server for every node and keeps the fields the command
/// prints.
async fn list_nodes() -> Result<Vec<NodeInfo>, kube::Error> {
    let client = Client::try_default().await?;
    let nodes = Api::<Node>::all(client)
        .list(&ListParams::default())
        .await?;
    Ok(nodes
        .into_iter()
        .map(|node| {
            let status = node.status.unwrap_or_default();
            let info = status.node_info.unwrap_or_default();
            let gpus = status
                .allocatable
                .and_then(|resources| resources.get("nvidia.com/gpu")?.0.parse().ok())
                .unwrap_or(0);
            NodeInfo {
                name: node.metadata.name.unwrap_or_default(),
                gpus,
                arch: info.architecture,
                os: info.operating_system,
                kubelet: info.kubelet_version,
            }
        })
        .collect())
}
// ANCHOR_END: nodes

// ANCHOR: output
/// Writes the rows as a table for a person or as JSON for a program.
fn print_nodes(rows: &[NodeInfo], json: bool) -> serde_json::Result<()> {
    if json {
        println!("{}", serde_json::to_string_pretty(rows)?);

        return Ok(());
    }

    let header = ["NAME", "GPUS", "ARCH", "OS", "KUBELET"].map(String::from);
    let table: Vec<[String; 5]> = std::iter::once(header)
        .chain(rows.iter().map(|r| {
            [
                r.name.clone(),
                r.gpus.to_string(),
                r.arch.clone(),
                r.os.clone(),
                r.kubelet.clone(),
            ]
        }))
        .collect();
    // Each column is as wide as its longest cell, plus two spaces.
    let widths: [usize; 5] =
        std::array::from_fn(|col| table.iter().map(|row| row[col].len()).max().unwrap_or(0));

    for row in &table {
        let line: String = (0..5)
            .map(|col| format!("{:<width$}", row[col], width = widths[col] + 2))
            .collect();
        println!("{}", line.trim_end());
    }

    Ok(())
}
// ANCHOR_END: output

/// Returns the platform in the form Go prints it, such as `linux/arm64`.
/// Rust calls the architectures `aarch64` and `x86_64`.
fn platform() -> String {
    let arch = match env::consts::ARCH {
        "aarch64" => "arm64",
        "x86_64" => "amd64",
        other => other,
    };

    format!("{}/{arch}", env::consts::OS)
}

// ANCHOR: run
/// Carries out one command line and returns the exit status.
async fn run(args: &[String]) -> ExitCode {
    let args: Vec<&str> = args.iter().map(String::as_str).collect();

    match args.as_slice() {
        ["version"] => println!("gpuctl {} {}", env!("CARGO_PKG_VERSION"), platform()),
        ["config"] => {
            let (Some(file), Some(kube)) = (config_file(), kubeconfig()) else {
                eprintln!("gpuctl: cannot find the home directory");

                return ExitCode::FAILURE;
            };
            println!(
                "config file  {}\nkubeconfig   {}",
                file.display(),
                kube.display()
            );
        }
        ["nodes"] | ["nodes", "-o", "table" | "json"] => {
            let json = args.last() == Some(&"json");
            let rows = match list_nodes().await {
                Ok(rows) => rows,
                Err(e) => {
                    eprintln!("gpuctl: {e}");

                    return ExitCode::FAILURE;
                }
            };

            if let Err(e) = print_nodes(&rows, json) {
                eprintln!("gpuctl: {e}");

                return ExitCode::FAILURE;
            }
        }
        [] | ["nodes", ..] => {
            eprint!("{USAGE}");

            return ExitCode::from(EXIT_USAGE);
        }
        [other, ..] => {
            eprint!("gpuctl: unknown command \"{other}\"\n{USAGE}");

            return ExitCode::from(EXIT_USAGE);
        }
    }

    ExitCode::SUCCESS
}

#[tokio::main]
async fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();

    run(&args).await
}
// ANCHOR_END: run
