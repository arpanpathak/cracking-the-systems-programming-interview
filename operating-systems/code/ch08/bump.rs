// ch08/bump.rs: A linear bump (arena) allocator with explicit power-of-two alignment.
use std::error::Error;
use std::io;
use std::ptr;

struct BumpAllocator {
    arena_base: *mut u8,    // Page-aligned start address returned by mmap()
    arena_capacity: usize,  // Total size of the virtual mapping in bytes
    next_offset: usize,     // Byte offset of the next unallocated byte
}

impl BumpAllocator {
    fn create(capacity_bytes: usize) -> io::Result<BumpAllocator> {
        // SAFETY: `libc::mmap` with `MAP_PRIVATE | MAP_ANON` allocates a fresh,
        // zero-initialized anonymous virtual memory region of `capacity_bytes`.
        // Checking `mapped != libc::MAP_FAILED` guarantees a valid page-aligned base pointer.
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

            Ok(BumpAllocator {
                arena_base: mapped.cast::<u8>(),
                arena_capacity: capacity_bytes,
                next_offset: 0,
            })
        }
    }

    // Allocates `requested_bytes` aligned upward to a power-of-two `alignment` boundary.
    fn alloc(&mut self, requested_bytes: usize, alignment: usize) -> Option<*mut u8> {
        // Round `next_offset` up to the smallest multiple of `alignment` >= `next_offset`.
        // Example: next_offset = 11, alignment = 16:
        //   (11 + 15) & !15  =  26 & !15  =  16  (inserts 5 bytes of padding: 11..15).
        let aligned_offset = (self.next_offset + alignment - 1) & !(alignment - 1);
        if aligned_offset + requested_bytes > self.arena_capacity {
            return None;
        }

        self.next_offset = aligned_offset + requested_bytes;
        // SAFETY: The bounds check `aligned_offset + requested_bytes <= self.arena_capacity`
        // proves that `arena_base.add(aligned_offset)` remains strictly within the mapped arena.
        Some(unsafe { self.arena_base.add(aligned_offset) })
    }

    // Reclaims all allocations simultaneously by rewinding the bump pointer to zero.
    fn reset(&mut self) {
        self.next_offset = 0;
    }
}

impl Drop for BumpAllocator {
    fn drop(&mut self) {
        // SAFETY: `arena_base` and `arena_capacity` match the exact arguments from `mmap`.
        unsafe { libc::munmap(self.arena_base.cast::<libc::c_void>(), self.arena_capacity) };
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    let mut allocator = BumpAllocator::create(64 * 1024)?;
    println!("arena: {:p}, {} bytes\n", allocator.arena_base, allocator.arena_capacity);

    // 1. Offset 0 is already 8-byte aligned -> occupies bytes [0, 8), next_offset becomes 8.
    let first_block = allocator.alloc(8, 8).ok_or("arena exhausted on first_block")?;
    // 2. Offset 8 is already 8-byte aligned -> occupies bytes [8, 11), next_offset becomes 11.
    let small_block = allocator.alloc(3, 8).ok_or("arena exhausted on small_block")?;
    // 3. Offset 11 is NOT 16-byte aligned -> inserts 5 bytes of padding [11, 16),
    //    then allocates 16 bytes at [16, 32), advancing next_offset to 32.
    let aligned_block = allocator.alloc(16, 16).ok_or("arena exhausted on aligned_block")?;

    assert_eq!(first_block, allocator.arena_base);
    assert_eq!(small_block as usize - allocator.arena_base as usize, 8);
    assert_eq!(aligned_block as usize - allocator.arena_base as usize, 16);
    assert_eq!(allocator.next_offset, 32);

    println!("alloc(8,  align=8)  -> {first_block:p} (offset 0,  bytes 0..7)");
    println!("alloc(3,  align=8)  -> {small_block:p} (offset 8,  bytes 8..10)");
    println!("alloc(16, align=16) -> {aligned_block:p} (offset 16, bytes 16..31 after 5B padding)");
    println!("next_offset         -> {}\n", allocator.next_offset);

    // Resetting rewinds next_offset to 0 so the arena can be reused immediately.
    allocator.reset();
    let reused_block = allocator.alloc(8, 8).ok_or("arena exhausted after reset")?;
    assert_eq!(reused_block, first_block);
    println!("after reset, alloc(8, align=8) -> {reused_block:p} (reuses offset 0: yes)");
    Ok(())
}
