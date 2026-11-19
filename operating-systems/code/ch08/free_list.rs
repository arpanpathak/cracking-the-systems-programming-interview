// ch08/free_list.rs: first-fit with headers, splitting, and coalescing in Rust.
use std::process::exit;
use std::ptr;

#[derive(Clone, Copy)]
struct Block {
    size: usize,   // payload bytes available in this block
    free: bool,
    next: *mut Block,
}

const HEADER: usize = std::mem::size_of::<Block>();

struct Heap {
    base: *mut u8,
    size: usize,
    free_head: *mut Block,
}

impl Heap {
    fn create(bytes: usize) -> Heap {
        // SAFETY:
        // `mmap` requests a private, anonymous virtual memory mapping.
        // `bytes` defines the contiguous arena size. Upon verifying `p != MAP_FAILED`,
        // `p` is page-aligned and guaranteed by the kernel to be isolated from any other
        // memory region. We write the initial root `Block` header spanning the entire arena,
        // establishing the base inductive state for the intrusive linked list.
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

            let head = p.cast::<Block>();
            ptr::write(
                head,
                Block { size: bytes - HEADER, free: true, next: ptr::null_mut() },
            );

            Heap { base: p.cast::<u8>(), size: bytes, free_head: head }
        }
    }

    fn alloc(&mut self, n: usize) -> Option<*mut u8> {
        let mut b = self.free_head;
        while !b.is_null() {
            // SAFETY: Invariant Proof:
            // 1. `b` is verified non-null and originates from `self.free_head` or a valid `(*b).next` pointer.
            // 2. Structural induction ensures every node in the intrusive chain points to an initialized,
            //    in-bounds `Block` header inside `[self.base, self.base + self.size)`.
            // 3. When `rest >= HEADER + 16`, the split boundary `nb = b + HEADER + n` is guaranteed
            //    to reside strictly inside the current block's payload span, ensuring the newly
            //    carved header does not collide with neighboring allocations.
            unsafe {
                if (*b).free && (*b).size >= n {
                    let rest = (*b).size - n;
                    if rest >= HEADER + 16 {
                        // Split: carve a free block out of the remainder.
                        let nb = b.cast::<u8>().add(HEADER + n).cast::<Block>();
                        ptr::write(
                            nb,
                            Block { size: rest - HEADER, free: true, next: (*b).next },
                        );

                        (*b).size = n;
                        (*b).next = nb;
                    }

                    (*b).free = false;
                    return Some(b.cast::<u8>().add(HEADER));
                }

                b = (*b).next;
            }
        }

        None
    }

    fn free(&mut self, p: *mut u8) {
        // SAFETY: Allocator Contract Proof:
        // `p` was returned by a preceding call to `alloc()`. In our layout geometry, the user payload
        // begins exactly `HEADER` bytes after the start of the `Block` header. Subtracting `HEADER`
        // reconstructs the original, valid header pointer `b`. Marking `(*b).free = true` returns
        // ownership of this slice to the allocator pool.
        unsafe {
            let b = p.sub(HEADER).cast::<Block>();
            (*b).free = true;
        }

        self.coalesce();
    }

    fn coalesce(&mut self) {
        let mut b = self.free_head;
        // SAFETY: Coalescing Invariant Proof:
        // `b` and `n = (*b).next` are active, initialized headers.
        // Adjacency verification `n == b + HEADER + (*b).size` proves that no allocated or unmapped
        // space exists between block `b` and block `n`. Merging them by extending `(*b).size` by
        // `HEADER + (*n).size` and splicing `(*b).next = (*n).next` eliminates internal header
        // fragmentation without violating any memory boundaries.
        unsafe {
            while !b.is_null() && !(*b).next.is_null() {
                let n = (*b).next;
                let b_end = b.cast::<u8>().add(HEADER + (*b).size);
                let adjacent = n.cast::<u8>() == b_end;

                if (*b).free && (*n).free && adjacent {
                    (*b).size += HEADER + (*n).size;
                    (*b).next = (*n).next;
                } else {
                    b = n;
                }
            }
        }
    }

    fn dump(&self) {
        println!("  block map:");

        let mut b = self.free_head;
        let mut i = 0;
        // SAFETY: Safe read-only traversal of the validated intrusive header list.
        unsafe {
            while !b.is_null() {
                let off = b.cast::<u8>() as usize - self.base as usize;
                println!(
                    "    [{i}] offset {off} size {} {}",
                    (*b).size,
                    if (*b).free { "free" } else { "used" }
                );

                b = (*b).next;
                i += 1;
            }
        }
    }
}

impl Drop for Heap {
    fn drop(&mut self) {
        // SAFETY: `munmap` releases the virtual memory mapping allocated in `create()`.
        // By RAII, `drop` is invoked only once when the `Heap` instance exits scope.
        unsafe { libc::munmap(self.base.cast::<libc::c_void>(), self.size) };
    }
}

fn main() {
    let mut h = Heap::create(256 * 1024);
    println!("arena: {:p}, {} bytes, header {} bytes\n", h.base, h.size, HEADER);

    let a = h.alloc(100).unwrap();
    let b = h.alloc(200).unwrap();
    let c = h.alloc(300).unwrap();

    println!("after alloc(100), alloc(200), alloc(300):");
    h.dump();

    h.free(b);
    println!("\nafter free(b):");
    h.dump();

    let d = h.alloc(150).unwrap();
    println!("\nafter alloc(150) into the hole left by b:");
    h.dump();
    println!("d reuses b's block: {}", d == b);

    h.free(a);
    h.free(d);
    h.free(c);

    println!("\nafter freeing everything:");
    h.dump();
}
