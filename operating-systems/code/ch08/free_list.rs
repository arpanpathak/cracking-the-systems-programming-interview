// ch08/free_list.rs: First-fit free-list allocator with in-band headers,
// block splitting, and adjacent free-block coalescing in Rust.
// Written with flat control flow (early returns and small helpers) to keep logic clear.
use std::error::Error;
use std::io;
use std::ptr;

#[derive(Clone, Copy)]
struct BlockHeader {
    payload_bytes: usize,
    is_free: bool,
    next_block: *mut BlockHeader,
}

const HEADER_BYTES: usize = std::mem::size_of::<BlockHeader>();
const MIN_SPLIT_PAYLOAD: usize = 16;

struct FreeListHeap {
    arena_base: *mut u8,
    arena_capacity: usize,
    head_block: *mut BlockHeader,
}

impl FreeListHeap {
    fn create(capacity_bytes: usize) -> io::Result<FreeListHeap> {
        // SAFETY: `mmap` allocates a page-aligned, zero-initialized anonymous region.
        // After verifying `mapped != MAP_FAILED`, we initialize a single root BlockHeader at offset 0.
        unsafe {
            let mapped = libc::mmap(
                ptr::null_mut(),
                capacity_bytes,
                libc::PROT_READ | libc::PROT_WRITE,
                libc::MAP_PRIVATE | libc::MAP_ANON,
                -1,
                0,
            );
            if mapped == libc::MAP_FAILED {
                return Err(io::Error::last_os_error());
            }

            let initial_header = mapped.cast::<BlockHeader>();
            ptr::write(
                initial_header,
                BlockHeader {
                    payload_bytes: capacity_bytes - HEADER_BYTES,
                    is_free: true,
                    next_block: ptr::null_mut(),
                },
            );

            Ok(FreeListHeap {
                arena_base: mapped.cast::<u8>(),
                arena_capacity: capacity_bytes,
                head_block: initial_header,
            })
        }
    }

    // Splits `block` if leftover bytes fit a new BlockHeader plus >= MIN_SPLIT_PAYLOAD bytes.
    // SAFETY: Caller guarantees `block` is a valid initialized header with `payload_bytes >= requested_bytes`.
    unsafe fn split_if_large_enough(block: *mut BlockHeader, requested_bytes: usize) {
        let leftover_bytes = unsafe { (*block).payload_bytes - requested_bytes };
        if leftover_bytes < HEADER_BYTES + MIN_SPLIT_PAYLOAD {
            return;
        }

        // SAFETY: `HEADER_BYTES + requested_bytes` lies strictly inside `block`'s payload span.
        unsafe {
            let split_header = block
                .cast::<u8>()
                .add(HEADER_BYTES + requested_bytes)
                .cast::<BlockHeader>();
            ptr::write(
                split_header,
                BlockHeader {
                    payload_bytes: leftover_bytes - HEADER_BYTES,
                    is_free: true,
                    next_block: (*block).next_block,
                },
            );
            (*block).payload_bytes = requested_bytes;
            (*block).next_block = split_header;
        }
    }

    // Returns true when `current` and `neighbor` are both free and physically contiguous.
    // SAFETY: Caller guarantees both pointers refer to valid initialized headers inside the arena.
    unsafe fn can_coalesce(current: *const BlockHeader, neighbor: *const BlockHeader) -> bool {
        unsafe {
            if !(*current).is_free || !(*neighbor).is_free {
                return false;
            }
            let current_end = current
                .cast::<u8>()
                .add(HEADER_BYTES + (*current).payload_bytes);
            neighbor.cast::<u8>() == current_end
        }
    }

    // First-fit allocation: scans the block chain with flat guard clauses.
    fn alloc(&mut self, requested_bytes: usize) -> Option<*mut u8> {
        let mut current = self.head_block;
        while !current.is_null() {
            // SAFETY: Every pointer in the intrusive list is an initialized in-bounds BlockHeader.
            unsafe {
                if !(*current).is_free || (*current).payload_bytes < requested_bytes {
                    current = (*current).next_block;
                    continue;
                }
                Self::split_if_large_enough(current, requested_bytes);
                (*current).is_free = false;
                return Some(current.cast::<u8>().add(HEADER_BYTES));
            }
        }
        None
    }

    // Releases a payload pointer and merges any physically adjacent free blocks.
    fn free(&mut self, user_payload_ptr: *mut u8) {
        // SAFETY: `user_payload_ptr` was returned by `alloc()` at `header + HEADER_BYTES`.
        unsafe {
            let header = user_payload_ptr.sub(HEADER_BYTES).cast::<BlockHeader>();
            (*header).is_free = true;
        }
        self.coalesce_adjacent_free_blocks();
    }

    fn coalesce_adjacent_free_blocks(&mut self) {
        let mut current = self.head_block;
        // SAFETY: `current` and `neighbor` are valid initialized headers within the arena.
        unsafe {
            while !current.is_null() && !(*current).next_block.is_null() {
                let neighbor = (*current).next_block;
                if !Self::can_coalesce(current, neighbor) {
                    current = neighbor;
                    continue;
                }
                // Absorb both the neighbor's payload and its redundant 24-byte header.
                (*current).payload_bytes += HEADER_BYTES + (*neighbor).payload_bytes;
                (*current).next_block = (*neighbor).next_block;
            }
        }
    }

    fn dump_block_map(&self) {
        println!("  block map:");
        let mut current = self.head_block;
        let mut block_index = 0;
        // SAFETY: Read-only traversal of the validated intrusive header list.
        unsafe {
            while !current.is_null() {
                let byte_offset = current.cast::<u8>() as usize - self.arena_base as usize;
                println!(
                    "    [{block_index}] offset {byte_offset}  payload {}  {}",
                    (*current).payload_bytes,
                    if (*current).is_free { "free" } else { "used" }
                );
                current = (*current).next_block;
                block_index += 1;
            }
        }
    }
}

impl Drop for FreeListHeap {
    fn drop(&mut self) {
        // SAFETY: Unmaps the exact virtual region created in `create()`.
        unsafe { libc::munmap(self.arena_base.cast::<libc::c_void>(), self.arena_capacity) };
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    let mut heap = FreeListHeap::create(256 * 1024)?;
    println!(
        "arena: {:p}, {} bytes, header {} bytes\n",
        heap.arena_base, heap.arena_capacity, HEADER_BYTES
    );

    let block_a = heap.alloc(100).ok_or("heap exhausted on block_a")?;
    let block_b = heap.alloc(200).ok_or("heap exhausted on block_b")?;
    let block_c = heap.alloc(300).ok_or("heap exhausted on block_c")?;

    println!("after alloc(100), alloc(200), alloc(300):");
    heap.dump_block_map();

    heap.free(block_b);
    println!("\nafter free(block_b):");
    heap.dump_block_map();

    let block_d = heap.alloc(150).ok_or("heap exhausted on block_d")?;
    assert_eq!(block_d, block_b);
    println!("\nafter alloc(150) into block_b's hole:");
    heap.dump_block_map();
    println!("block_d reuses block_b's address: yes");

    heap.free(block_a);
    heap.free(block_d);
    heap.free(block_c);
    // SAFETY: `head_block` is always a valid initialized header spanning the coalesced arena.
    unsafe {
        assert!((*heap.head_block).is_free && (*heap.head_block).next_block.is_null());
    }

    println!("\nafter freeing all blocks (coalesced back to 1 free block):");
    heap.dump_block_map();
    Ok(())
}
