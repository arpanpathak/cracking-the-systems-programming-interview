// ch03/layout.rs: the same address-space regions, observed from Rust.
use std::ptr::addr_of;
use std::sync::atomic::AtomicI32;

fn anchor() {}

static G_INITIALIZED: AtomicI32 = AtomicI32::new(42);
static mut G_UNINITIALIZED: i32 = 0;

fn main() {
    let stack_local = 7i32;       // stack
    let heap = Box::new(99i32);   // heap

    println!(
        "text   (fn anchor)     : {:#x}\n\
         data   (static atomic) : {:#x}\n\
         bss    (static mut)    : {:#x}\n\
         heap   (Box<i32>)      : {:#x}\n\
         stack  (local)         : {:#x}",
        anchor as *const () as usize,
        &G_INITIALIZED as *const _ as usize,
        addr_of!(G_UNINITIALIZED) as usize,
        &*heap as *const i32 as usize,
        &stack_local as *const i32 as usize,
    );
}
