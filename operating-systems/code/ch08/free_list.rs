// ch08/free_list.rs: First-fit free-list allocator with in-band headers,
// block splitting, and adjacent free-block coalescing in Rust.
use std::process::exit;
use std::ptr;

// Metadata stored immediately before every user payload (24 bytes on 64-bit systems).
#[derive(Clone, Copy)]
struct BlockHeader {
    payload_bytes: usize,       // Usable payload bytes immediately following this header
    is_free: bool,              // true = available for allocation; false = owned by caller
    next_block: *mut BlockHeader, // Next block in physical address order inside the arena
}

const HEADER_BYTES: usize = std::mem::size_of::<BlockHeader>();
// Minimum usable payload required before splitting a free block, preventing tiny fragments.
const MIN_SPLIT_PAYLOAD: usize = 16;

struct FreeListHeap {
    arena_base: *mut u8,
    arena_capacity: usize,
    head_block: *mut BlockHeader,
}

impl FreeListHeap {
    fn create(capacity_bytes: usize) -> FreeListHeap {
        // SAFETY: `mmap` allocates a page-aligned, isolated private mapping of `capacity_bytes`.
        // After verifying `mapped != libc::MAP_FAILED`, we initialize a single root `BlockHeader`
        // at offset 0 spanning the entire arena.
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
                eprintln!("mmap failed");
                exit(1);
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

            FreeListHeap {
                arena_base: mapped.cast::<u8>(),
                arena_capacity: capacity_bytes,
                head_block: initial_header,
            }
        }
    }

    // First-fit allocation: finds the first free block large enough for `requested_bytes`.
    fn alloc(&mut self, requested_bytes: usize) -> Option<*mut u8> {
        let mut current = self.head_block;
        while !current.is_null() {
            // SAFETY: Every pointer in the intrusive list resides inside `[arena_base, arena_base + arena_capacity)`
            // and points to an initialized `BlockHeader`. When `leftover_bytes >= HEADER_BYTES + MIN_SPLIT_PAYLOAD`,
            // the split header at `current + HEADER_BYTES + requested_bytes` lies strictly inside `current`'s payload.
            unsafe {
                if (*current).is_free && (*current).payload_bytes >= requested_bytes {
                    let leftover_bytes = (*current).payload_bytes - requested_bytes;
                    if leftover_bytes >= HEADER_BYTES + MIN_SPLIT_PAYLOAD {
                        let split_header = current
                            .cast::<u8>()
                            .add(HEADER_BYTES + requested_bytes)
                            .cast::<BlockHeader>();

                        ptr::write(
                            split_header,
                            BlockHeader {
                                payload_bytes: leftover_bytes - HEADER_BYTES,
                                is_free: true,
                                next_block: (*current).next_block,
                            },
                        );

                        (*current).payload_bytes = requested_bytes;
                        (*current).next_block = split_header;
                    }

                    (*current).is_free = false;
                    // Advance past the 24-byte header to return the start of the user payload.
                    return Some(current.cast::<u8>().add(HEADER_BYTES));
                }

                current = (*current).next_block;
            }
        }

        None
    }

    // Releases a previously allocated payload pointer and merges adjacent free blocks.
    fn free(&mut self, user_payload_ptr: *mut u8) {
        // SAFETY: `user_payload_ptr` was returned by `alloc()` at `header + HEADER_BYTES`.
        // Stepping backward by `HEADER_BYTES` recovers the initialized `BlockHeader`.
        unsafe {
            let header = user_payload_ptr.sub(HEADER_BYTES).cast::<BlockHeader>();
            (*header).is_free = true;
        }

        self.coalesce_adjacent_free_blocks();
    }

    // Linear pass merging any two physically adjacent free blocks into one larger block.
    fn coalesce_adjacent_free_blocks(&mut self) {
        let mut current = self.head_block;
        // SAFETY: `current` and `neighbor` are valid initialized headers within the arena.
        // Verifying `neighbor == current + HEADER_BYTES + current.payload_bytes` confirms
        // physical adjacency before absorbing `neighbor`'s header and payload into `current`.
        unsafe {
            while !current.is_null() && !(*current).next_block.is_null() {
                let neighbor = (*current).next_block;
                let current_end_addr = current
                    .cast::<u8>()
                    .add(HEADER_BYTES + (*current).payload_bytes);
                let is_physically_adjacent = neighbor.cast::<u8>() == current_end_addr;

                if (*current).is_free && (*neighbor).is_free && is_physically_adjacent {
                    (*current).payload_bytes += HEADER_BYTES + (*neighbor).payload_bytes;
                    (*current).next_block = (*neighbor).next_block;
                } else {
                    current = neighbor;
                }
            }
        }
    }

    fn dump_block_map(&self) {
        println!("  block map:");
        let mut current = self.head_block;
        let mut block_index = 0;
        // SAFETY: Read-only traversal of the validated intrusive block header chain.
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
        // SAFETY: Releases the exact virtual mapping allocated in `create()`.
        unsafe { libc::munmap(self.arena_base.cast::<libc::c_void>(), self.arena_capacity) };
    }
}

fn main() {
    let mut heap = FreeListHeap::create(256 * 1024);
    println!(
        "arena: {:p}, {} bytes, header {} bytes\n",
        heap.arena_base, heap.arena_capacity, HEADER_BYTES
    );

    let block_a = heap.alloc(100).unwrap();
    let block_b = heap.alloc(200).unwrap();
    let block_c = heap.alloc(300).unwrap();

    println!("after alloc(100), alloc(200), alloc(300):");
    heap.dump_block_map();

    heap.free(block_b);
    println!("\nafter free(block_b):");
    heap.dump_block_map();

    // Reuses block_b's 200-byte hole: 150B used + 24B new header + 26B free remainder.
    let block_d = heap.alloc(150).unwrap();
    println!("\nafter alloc(150) into block_b's hole:");
    heap.dump_block_map();
    println!(
        "block_d reuses block_b's address: {}",
        if block_d == block_b { "yes" } else { "no" }
    );

    heap.free(block_a);
    heap.free(block_d);
    heap.free(block_c);

    println!("\nafter freeing all blocks (coalesced back to 1 free block):");
    heap.dump_block_map();
}
