//! Small algebraic-data-type idioms that are quick to write under time pressure.
//!
//! These are the patterns worth reaching for in a live coding round because they
//! are short, they cannot represent invalid states, and they show the reviewer
//! that the design is deliberate rather than improvised.
//!
//! - A newtype gives a primitive a name and a single validating constructor, so
//!   an out-of-range value cannot exist.
//! - An enum with data models a closed set of alternatives, and `match` forces
//!   every alternative to be handled.
//! - Typed errors carry the reason instead of a string, so the caller can react.
//! - `TryFrom` puts the validation on the type boundary, where it belongs.
//! - An iterator chain states the intent in one pass and removes index
//!   bookkeeping.

use std::fmt;

/// A GPU count that is validated at construction.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct GpuCount(u32);

impl GpuCount {
    pub const MIN: u32 = 1;
    pub const MAX: u32 = 64;

    /// Validate a raw count.
    pub fn new(value: u32) -> Result<Self, GpuCountError> {
        if (Self::MIN..=Self::MAX).contains(&value) {
            Ok(Self(value))
        } else {
            Err(GpuCountError(value))
        }
    }

    pub fn get(self) -> u32 {
        self.0
    }
}

/// Why a raw GPU count was rejected.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GpuCountError(pub u32);

impl fmt::Display for GpuCountError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "gpu count {} is outside {}..={}",
            self.0,
            GpuCount::MIN,
            GpuCount::MAX
        )
    }
}

impl std::error::Error for GpuCountError {}

impl TryFrom<u32> for GpuCount {
    type Error = GpuCountError;

    fn try_from(value: u32) -> Result<Self, Self::Error> {
        Self::new(value)
    }
}

impl From<GpuCount> for u32 {
    fn from(count: GpuCount) -> u32 {
        count.0
    }
}

/// A closed set of commands, each carrying exactly the data it needs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Command {
    List,
    Get { id: String },
    Create { name: String, gpus: GpuCount },
    Delete { id: String },
}

impl Command {
    /// Parse one command line.
    pub fn parse(line: &str) -> Result<Self, CommandError> {
        let mut parts = line.split_whitespace();
        let verb = parts.next().ok_or(CommandError::Empty)?;

        match verb {
            "list" => Ok(Self::List),
            "get" => Ok(Self::Get {
                id: argument(&mut parts, "id")?.to_string(),
            }),
            "delete" => Ok(Self::Delete {
                id: argument(&mut parts, "id")?.to_string(),
            }),
            "create" => {
                let name = argument(&mut parts, "name")?.to_string();
                let raw = argument(&mut parts, "gpu count")?;
                let value: u32 = raw
                    .parse()
                    .map_err(|_| CommandError::InvalidGpuCount(raw.to_string()))?;
                let gpus = GpuCount::new(value)
                    .map_err(|_| CommandError::InvalidGpuCount(raw.to_string()))?;
                Ok(Self::Create { name, gpus })
            }
            other => Err(CommandError::UnknownVerb(other.to_string())),
        }
    }

    pub fn verb(&self) -> &'static str {
        match self {
            Self::List => "list",
            Self::Get { .. } => "get",
            Self::Create { .. } => "create",
            Self::Delete { .. } => "delete",
        }
    }
}

/// A typed parse failure, so callers can distinguish the cases.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CommandError {
    Empty,
    UnknownVerb(String),
    MissingArgument(&'static str),
    InvalidGpuCount(String),
}

impl fmt::Display for CommandError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => write!(formatter, "empty command"),
            Self::UnknownVerb(verb) => write!(formatter, "unknown verb {verb:?}"),
            Self::MissingArgument(name) => write!(formatter, "missing argument: {name}"),
            Self::InvalidGpuCount(raw) => write!(formatter, "invalid gpu count: {raw:?}"),
        }
    }
}

impl std::error::Error for CommandError {}

fn argument<'a>(
    parts: &mut impl Iterator<Item = &'a str>,
    name: &'static str,
) -> Result<&'a str, CommandError> {
    parts.next().ok_or(CommandError::MissingArgument(name))
}

/// Count and sum in one pass, without managing an index.
pub fn summarize(values: &[i32]) -> (usize, i64) {
    values.iter().fold((0usize, 0i64), |(count, sum), value| {
        (count + 1, sum + i64::from(*value))
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_each_command_variant() {
        assert_eq!(Command::parse("list"), Ok(Command::List));
        assert_eq!(
            Command::parse("get wl-7"),
            Ok(Command::Get { id: "wl-7".into() })
        );
        assert_eq!(
            Command::parse("create triton 4"),
            Ok(Command::Create {
                name: "triton".into(),
                gpus: GpuCount::new(4).expect("valid")
            })
        );
        assert_eq!(
            Command::parse("delete wl-7"),
            Ok(Command::Delete { id: "wl-7".into() })
        );
    }

    #[test]
    fn rejects_bad_input_with_typed_errors() {
        assert_eq!(Command::parse(""), Err(CommandError::Empty));
        assert_eq!(
            Command::parse("frobnicate"),
            Err(CommandError::UnknownVerb("frobnicate".into()))
        );
        assert_eq!(
            Command::parse("get"),
            Err(CommandError::MissingArgument("id"))
        );
        assert_eq!(
            Command::parse("create triton 0"),
            Err(CommandError::InvalidGpuCount("0".into()))
        );
        assert_eq!(
            Command::parse("create triton many"),
            Err(CommandError::InvalidGpuCount("many".into()))
        );
    }

    #[test]
    fn newtype_rejects_out_of_range_values() {
        assert!(GpuCount::new(1).is_ok());
        assert!(GpuCount::new(64).is_ok());
        assert!(GpuCount::new(0).is_err());
        assert!(GpuCount::new(65).is_err());
        assert_eq!(u32::from(GpuCount::try_from(8).expect("valid")), 8);
        assert!(GpuCount::try_from(0).is_err());
    }

    #[test]
    fn summarize_reports_count_and_sum() {
        assert_eq!(summarize(&[]), (0, 0));
        assert_eq!(summarize(&[1, 2, 3]), (3, 6));
        assert_eq!(summarize(&[-5, 5]), (2, 0));
    }

    #[test]
    fn errors_render_a_reason() {
        assert_eq!(
            Command::parse("create triton 0").unwrap_err().to_string(),
            "invalid gpu count: \"0\""
        );
        assert!(
            GpuCount::new(99)
                .unwrap_err()
                .to_string()
                .contains("outside")
        );
    }
}
