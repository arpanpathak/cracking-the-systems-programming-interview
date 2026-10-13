//! A small shell. It parses a command line into a pipeline of commands with
//! redirections, starts each command with its descriptors arranged, waits for
//! all of them, and reports the status of the last. The commands cd and exit
//! are built in.
//!
//! Without arguments it runs a fixed script in a temporary directory. With -i
//! it reads command lines from standard input.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p msh
//! ```

// ANCHOR: imports
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, PipeReader, Write};
use std::os::unix::process::ExitStatusExt;
use std::process::{self, Child, Stdio};
// ANCHOR_END: imports

// ANCHOR: parse
/// One stage of a pipeline: its arguments and the files that replace its
/// standard input and output, when the line names any.
#[derive(Default)]
struct Command {
    args: Vec<String>,
    input: Option<String>,
    output: Option<String>,
    append_output: bool,
}

struct SyntaxError;

/// Splits a line into the commands of a pipeline. Words and operators are
/// separated by spaces. The operators are | < > and >>.
fn parse(line: &str) -> Result<Vec<Command>, SyntaxError> {
    let mut pipeline = Vec::new();
    let mut current = Command::default();
    let mut words = line.split_whitespace();

    while let Some(word) = words.next() {
        match word {
            "|" => {
                if current.args.is_empty() {
                    return Err(SyntaxError);
                }

                pipeline.push(std::mem::take(&mut current));
            }
            "<" | ">" | ">>" => {
                let file = words.next().ok_or(SyntaxError)?.to_owned();

                if word == "<" {
                    current.input = Some(file);
                } else {
                    current.output = Some(file);
                    current.append_output = word == ">>";
                }
            }
            _ => current.args.push(word.to_owned()),
        }
    }

    if current.args.is_empty() {
        return Err(SyntaxError);
    }

    pipeline.push(current);

    Ok(pipeline)
}
// ANCHOR_END: parse

// ANCHOR: files
/// Opens the files a command names and returns the files to use as its
/// standard input and output. `None` means "keep the default".
fn redirect(command: &Command) -> io::Result<(Option<File>, Option<File>)> {
    let input = command.input.as_ref().map(File::open).transpose()?;

    let output = command
        .output
        .as_ref()
        .map(|path| {
            OpenOptions::new()
                .write(true)
                .create(true)
                .append(command.append_output)
                .truncate(!command.append_output)
                .open(path)
        })
        .transpose()?;

    Ok((input, output))
}
// ANCHOR_END: files

// ANCHOR: launch
/// Starts every command of a pipeline and returns the children that started.
/// Command `i` reads from the pipe that command `i - 1` writes to, unless a
/// redirection replaces that descriptor.
fn launch(pipeline: &[Command]) -> Vec<Child> {
    let mut started = Vec::new();
    let mut from_previous: Option<PipeReader> = None;

    for (i, command) in pipeline.iter().enumerate() {
        let mut stdin = from_previous
            .take()
            .map_or_else(Stdio::inherit, Stdio::from);
        let mut stdout = Stdio::inherit();

        if i + 1 < pipeline.len() {
            let Ok((reader, writer)) = io::pipe() else {
                eprintln!("msh: cannot create a pipe");

                break;
            };

            stdout = writer.into();
            from_previous = Some(reader);
        }

        let (input, output) = match redirect(command) {
            Ok(files) => files,
            Err(error) => {
                eprintln!("msh: {error}");

                continue;
            }
        };

        if let Some(file) = input {
            stdin = file.into();
        }

        if let Some(file) = output {
            stdout = file.into();
        }

        // The `Command` owns the shell's copies of the descriptors. It is
        // dropped when the statement ends, which closes them.
        let child = process::Command::new(&command.args[0])
            .args(&command.args[1..])
            .stdin(stdin)
            .stdout(stdout)
            .spawn();

        match child {
            Ok(child) => started.push(child),
            Err(error) if error.kind() == io::ErrorKind::NotFound => {
                eprintln!("msh: {}: command not found", command.args[0]);
            }
            Err(error) => eprintln!("msh: {error}"),
        }
    }

    started
}
// ANCHOR_END: launch

// ANCHOR: wait
/// Converts a wait status to the number a shell reports: the exit status, or
/// 128 plus the signal number.
fn status(child: &mut Child) -> i32 {
    let Ok(status) = child.wait() else {
        return 127;
    };

    match (status.signal(), status.code()) {
        (Some(signal), _) => 128 + signal,
        (None, Some(code)) => code,
        (None, None) => 127,
    }
}

/// Starts a pipeline, waits for every command, and returns the status of the
/// last command, or 127 when the last command did not start.
fn run(pipeline: &[Command]) -> i32 {
    let mut started = launch(pipeline);
    let mut last = 127;

    for child in &mut started {
        last = status(child);
    }

    if started.len() < pipeline.len() {
        return 127;
    }

    last
}
// ANCHOR_END: wait

// ANCHOR: builtin
/// The state that outlives a command line.
#[derive(Default)]
struct Shell {
    last: i32,
    exiting: bool,
}

impl Shell {
    /// Runs one command line. cd and exit change the shell process itself, so
    /// they run inside it. Everything else runs in child processes.
    fn execute(&mut self, line: &str) {
        let Ok(pipeline) = parse(line) else {
            eprintln!("msh: syntax error");
            self.last = 2;

            return;
        };

        let args: Vec<&str> = pipeline[0].args.iter().map(String::as_str).collect();

        match (pipeline.len(), args.as_slice()) {
            (1, ["cd", directory]) => {
                self.last = 0;

                if let Err(error) = env::set_current_dir(directory) {
                    eprintln!("msh: {error}");
                    self.last = 1;
                }
            }
            (1, ["exit", rest @ ..]) => {
                self.exiting = true;

                if let [code] = rest
                    && let Ok(code) = code.parse()
                {
                    self.last = code;
                }
            }
            _ => self.last = run(&pipeline),
        }
    }
}
// ANCHOR_END: builtin

// ANCHOR: script
/// The demonstration that msh runs without arguments.
const SCRIPT: [&str; 10] = [
    "seq 1 5 > numbers",
    "wc -l < numbers",
    "sort -rn < numbers | head -n 2 >> numbers",
    "paste -sd, numbers",
    "false",
    "nosuchcommand",
    "cd /",
    "pwd",
    "exit 3",
    "echo not reached",
];

/// Runs the script in a new temporary directory and prints the status after
/// each line.
fn demonstrate() -> io::Result<()> {
    let dir = env::temp_dir().join(format!("msh-{}", process::id()));

    fs::create_dir_all(&dir)?;
    env::set_current_dir(&dir)?;

    let mut shell = Shell::default();

    for line in SCRIPT {
        println!("$ {line}");
        shell.execute(line);

        if shell.exiting {
            println!("[the shell exits with status {}]", shell.last);

            break;
        }

        println!("[status {}]", shell.last);
    }

    fs::remove_dir_all(&dir)
}

/// Reads command lines from standard input until exit or the end of the
/// input, and ends the process with the last status.
fn interact() -> io::Result<()> {
    let mut shell = Shell::default();
    let mut lines = io::stdin().lock().lines();

    while !shell.exiting {
        print!("msh$ ");
        io::stdout().flush()?;

        let Some(line) = lines.next().transpose()? else {
            break;
        };

        if !line.trim().is_empty() {
            shell.execute(&line);
        }
    }

    process::exit(shell.last);
}

fn main() -> io::Result<()> {
    if env::args().nth(1).as_deref() == Some("-i") {
        interact()?;
    }

    demonstrate()
}
// ANCHOR_END: script
