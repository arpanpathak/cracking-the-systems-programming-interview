using std::collctions::HashMap;

fn main() {
    let mut map = HashMap<i32>::new();

    map.insert(2, "Name");

    println!("Map value got {}", map.get(2).unwrap_or("Abc"));
}
