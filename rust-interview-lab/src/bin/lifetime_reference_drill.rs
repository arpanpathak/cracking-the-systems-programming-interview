use std::collections::HashMap;

#[derive(Debug)]
struct User {
    id: u32,
    name: String,
}

fn functional_numbers_drill(slice: &[i32]) -> Vec<i32> {
    slice.iter()
        .filter(|&&x| x % 2 == 0)
        .map(|&x| x * 10)
        .collect()
}

fn imperative_numbers_map(slice: &[i32]) -> HashMap<i32, i32> {
    let mut map = HashMap::new();
    for &num in slice {
        map.insert(num, num * 100);
    }
    map
}

fn struct_slice_to_map<'a>(slice: &'a [User]) -> HashMap<u32, &'a User> {
    let mut map = HashMap::new();
    for user in slice {
        map.insert(user.id, user);
    }
    map
}

fn ref_slice_to_map<'a>(slice: &[&'a User]) -> HashMap<u32, &'a User> {
    let mut map = HashMap::new();
    for &user in slice {
        map.insert(user.id, user);
    }
    map
}

fn main() {
    let vv = vec![1,2,3,4,5,6];

    let filtered: Vec<i32> = vv.iter().filter(|x| *x % 2 == 0).copied().collect();
    println!("Filtered : {:?}", filtered);

    println!("--- Ultra-Lean Inline Slice Drill ---\n");

    let processed_nums = functional_numbers_drill(&[10, 15, 20, 25, 30]);
    println!("1. Functional Numbers (Even * 10): {:?}", processed_nums);

    let num_map = imperative_numbers_map(&[10, 15, 20, 25, 30]);
    println!("2. Imperative Numbers Map: {:?}", num_map);

    // explicit reference binding holding the inline array literal
    let users: &[User] = &[
        User { id: 101, name: "Alice".to_string()   },
        User { id: 102, name: "Bob".to_string()     },
        User { id: 103, name: "Charlie".to_string() },
    ];
    println!("\n3. Zero-Allocation Struct Map (From &[User]):");
    let struct_map = struct_slice_to_map(users);
    for (id, user_ref) in &struct_map {
        println!("   Key ID: {} -> Value Name: {}", id, user_ref.name);
    }

    // explicit reference binding holding the inline array of &User
    let user_refs: &[&User] = &[
        struct_map[&101],
        struct_map[&102],
    ];
    println!("\n4. Zero-Allocation Ref Slice Map (From &[&User]):");
    let ref_slice_map = ref_slice_to_map(user_refs);
    for (id, user_ref) in &ref_slice_map {
        println!("   Key ID: {} -> Value Name: {}", id, user_ref.name);
    }

    println!("\n--- Drill Completed Successfully! ---");
}
