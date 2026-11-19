// ch08/bump.rs: the same bump allocator in Rust.
use std::process::exit;
use std::ptr;

struct Bump {
    base: *mut u8,
    size: usize,
    offset: usize,
}

impl Bump {
    fn create(bytes: usize) -> Bump {
        // SAFETY:
        // `libc::mmap` allocates an anonymous private memory mapping (`MAP_ANON | MAP_PRIVATE`).
        // The null pointer argument leaves virtual address placement to the kernel's ASLR.
        // `bytes` represents the contiguous reservation size. We explicitly verify `p != MAP_FAILED`
        // before dereferencing, ensuring a valid, zero-initialized arena backed by demand-zero pages.
        unsafe {
            let p = libc::mmap(
                ptr::null_mut(),
                bytes,
                libc::PROT_READ | libc::PROT_WRITE,
                libc::MAP_PRIVATE | libc::MAP_ANON,
                -1,
                0,
            );
            if p == libc::MAP_FAILED {
                eprintln!("mmap failed");
                exit(1);
            }

            Bump { base: p.cast::<u8>(), size: bytes, offset: 0 }
        }
    }

    fn alloc(&mut self, n: usize, align: usize) -> Option<*mut u8> {
        // Mathematical Alignment Proof:
        // Assuming `align` is a power of two ($2^k$), `align - 1` has its lowest $k$ bits set to 1.
        // Adding `align - 1` rounds any unaligned offset up to or past the next multiple of $2^k$.
        // Bitwise AND with `!(align - 1)` clears the lower $k$ bits, producing the exact minimal
        // multiple of `align` that is $\ge \text{self.offset}$.
        let aligned = (self.offset + align - 1) & !(align - 1);
        if aligned + n > self.size {
            return None;
        }

        self.offset = aligned + n;
        // SAFETY: The bounds check `aligned + n <= self.size` guarantees that the computed
        // pointer offset `self.base + aligned` points strictly within the allocated arena
        // boundary, preventing buffer overruns beyond the mapped virtual page range.
        Some(unsafe { self.base.add(aligned) })
    }

    fn reset(&mut self) {
        self.offset = 0;
    }
}

impl Drop for Bump {
    fn drop(&mut self) {
        // SAFETY: `munmap` releases the virtual address reservation back to the kernel page tables.
        // `self.base` and `self.size` match the exact pointer and length returned by `mmap`.
        // By Rust's affine type system, `drop` consumes `self`, guaranteeing no dangling pointers
        // to this arena remain accessible through the allocator.
        unsafe { libc::munmap(self.base.cast::<libc::c_void>(), self.size) };
    }
}

fn main() {
    let mut b = Bump::create(64 * 1024);
    println!("arena: {:p}, {} bytes\n", b.base, b.size);

    let a = b.alloc(8, 8).unwrap();
    let c = b.alloc(3, 8).unwrap();
    let d = b.alloc(16, 16).unwrap();

    println!("alloc(8,8)   -> {a:p} (offset 0)");
    println!("alloc(3,8)   -> {c:p} (offset 8)");
    println!("alloc(16,16) -> {d:p} (offset 16)");

    // The only way to reuse memory is to reset the whole arena.
    b.reset();
    let e = b.alloc(8, 8).unwrap();
    println!("after reset, alloc(8,8) -> {e:p} (same as first: {})", e == a);
}
