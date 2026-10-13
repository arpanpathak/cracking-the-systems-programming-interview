//! Generates the Rust types and the gRPC client and server from the schema.
//! It needs the Protocol Buffers compiler, `protoc`, on the PATH.

fn main() -> Result<(), Box<dyn std::error::Error>> {
    tonic_prost_build::compile_protos("../proto/store.proto")?;

    Ok(())
}
