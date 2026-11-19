fn main() {
    let pid = unsafe { libc::getpid() };
    println!("pid={pid}");
}
