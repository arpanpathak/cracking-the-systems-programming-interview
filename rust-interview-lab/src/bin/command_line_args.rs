use std::env::args;
use std::process::ExitCode;

/// The options this program understands.
#[derive(Debug, PartialEq)]
struct Options {
    name: String,
    count: u32,
    verbose: bool,
}

impl Default for Options {
    fn default() -> Self {
        Self { name: String::from("world"), count: 1, verbose: false }
    }
}

/// Turn the arguments after the program name into `Options`.
fn parse(arguments: impl IntoIterator<Item = String>) -> Result<Options, String> {
    let mut options = Options::default();
    let mut arguments = arguments.into_iter();

    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--name" => {
                options.name = arguments.next().ok_or("--name needs a value")?;
            }
            "--count" => {
                let value = arguments.next().ok_or("--count needs a value")?;
                options.count = value
                    .parse()
                    .map_err(|_| format!("--count needs a number, got {value:?}"))?;
            }
            "--verbose" => options.verbose = true,
            other => return Err(format!("unknown argument {other:?}")),
        }
    }

    Ok(options)
}

fn main() -> ExitCode {
    let options = match parse(args().skip(1)) {
        Ok(options) => options,
        Err(message) => {
            eprintln!("error: {message}");
            eprintln!("usage: command_line_args [--name NAME] [--count N] [--verbose]");
            return ExitCode::FAILURE;
        }
    };

    for index in 0..options.count {
        if options.verbose {
            println!("[{index}] hello, {}", options.name);
        } else {
            println!("hello, {}", options.name);
        }
    }

    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse_args(arguments: &[&str]) -> Result<Options, String> {
        parse(arguments.iter().map(|value| value.to_string()))
    }

    #[test]
    fn defaults_apply_when_there_are_no_arguments() {
        assert_eq!(parse_args(&[]).unwrap(), Options::default());
    }

    #[test]
    fn a_value_option_consumes_the_next_argument() {
        let options = parse_args(&["--name", "ada", "--count", "3"]).unwrap();
        assert_eq!(options.name, "ada");
        assert_eq!(options.count, 3);
    }

    #[test]
    fn verbose_is_a_flag() {
        assert!(parse_args(&["--verbose"]).unwrap().verbose);
        assert!(!parse_args(&[]).unwrap().verbose);
    }

    #[test]
    fn a_value_option_without_a_value_is_an_error() {
        assert!(parse_args(&["--name"]).is_err());
        assert!(parse_args(&["--count"]).is_err());
    }

    #[test]
    fn a_non_numeric_count_is_an_error() {
        assert!(parse_args(&["--count", "many"]).is_err());
    }

    #[test]
    fn an_unknown_argument_is_an_error() {
        assert!(parse_args(&["--colour", "red"]).is_err());
        assert!(parse_args(&["extra"]).is_err());
    }
}
