//! The format of one record of the log.
//!
//! A record is a frame of 8 bytes followed by a payload:
//!
//! ```text
//! length: u32 | checksum: u32 | sequence: u64 | kind: u8 | key length: u16 | key | value
//! ```
//!
//! `length` counts the bytes of the payload and `checksum` is the CRC-32 of
//! the payload. All integers are little-endian.

// ANCHOR: imports
use crc32fast::hash;
// ANCHOR_END: imports

// ANCHOR: types
/// A change to the store.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Change {
    Put { key: String, value: Vec<u8> },
    Delete { key: String },
}

/// A change with its position in the log. Sequence numbers start at 1 and
/// grow by 1 with each record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Record {
    pub sequence: u64,
    pub change: Change,
}

/// The result of reading one record from the front of a slice of bytes.
#[derive(Debug, PartialEq, Eq)]
pub enum Decoded {
    /// A whole record, and the number of bytes it occupies.
    Record { record: Record, length: usize },
    /// The bytes end before the record does.
    Incomplete,
    /// The checksum does not match the payload, or the payload is malformed.
    Corrupt,
}

/// The bytes of a frame: the length and the checksum.
pub const FRAME: usize = 8;

/// The largest payload a record may have: a key, a value of 1 MiB, and the
/// fixed fields.
pub const MAX_PAYLOAD: usize = (1 << 20) + 1024;

const PUT: u8 = 1;
const DELETE: u8 = 2;
// ANCHOR_END: types

// ANCHOR: encode
impl Record {
    /// Returns the record as the bytes that are appended to the log.
    pub fn encode(&self) -> Vec<u8> {
        let (kind, key, value) = match &self.change {
            Change::Put { key, value } => (PUT, key, value.as_slice()),
            Change::Delete { key } => (DELETE, key, &[][..]),
        };

        let mut payload = Vec::with_capacity(11 + key.len() + value.len());
        payload.extend_from_slice(&self.sequence.to_le_bytes());
        payload.push(kind);
        payload.extend_from_slice(&(key.len() as u16).to_le_bytes());
        payload.extend_from_slice(key.as_bytes());
        payload.extend_from_slice(value);

        let mut bytes = Vec::with_capacity(FRAME + payload.len());
        bytes.extend_from_slice(&(payload.len() as u32).to_le_bytes());
        bytes.extend_from_slice(&hash(&payload).to_le_bytes());
        bytes.extend_from_slice(&payload);

        bytes
    }
}
// ANCHOR_END: encode

// ANCHOR: decode
impl Record {
    /// Reads the record at the front of `bytes`.
    pub fn decode(bytes: &[u8]) -> Decoded {
        let Some((length, rest)) = bytes.split_first_chunk::<4>() else {
            return Decoded::Incomplete;
        };
        let Some((checksum, rest)) = rest.split_first_chunk::<4>() else {
            return Decoded::Incomplete;
        };

        let length = u32::from_le_bytes(*length) as usize;

        if length > MAX_PAYLOAD {
            return Decoded::Corrupt;
        }

        let Some(payload) = rest.get(..length) else {
            return Decoded::Incomplete;
        };

        if hash(payload) != u32::from_le_bytes(*checksum) {
            return Decoded::Corrupt;
        }

        match parse(payload) {
            Some(record) => Decoded::Record {
                record,
                length: FRAME + length,
            },
            None => Decoded::Corrupt,
        }
    }
}

/// Splits a payload into its fields. It returns `None` for a payload that is
/// too short for its fields or has an unknown kind.
fn parse(payload: &[u8]) -> Option<Record> {
    let (sequence, rest) = payload.split_first_chunk::<8>()?;
    let (&kind, rest) = rest.split_first()?;
    let (key_length, rest) = rest.split_first_chunk::<2>()?;
    let (key, value) = rest.split_at_checked(u16::from_le_bytes(*key_length) as usize)?;
    let key = String::from_utf8(key.to_vec()).ok()?;

    let change = match (kind, value) {
        (PUT, value) => Change::Put {
            key,
            value: value.to_vec(),
        },
        (DELETE, []) => Change::Delete { key },
        (_unknown, _value) => return None,
    };

    Some(Record {
        sequence: u64::from_le_bytes(*sequence),
        change,
    })
}
// ANCHOR_END: decode
