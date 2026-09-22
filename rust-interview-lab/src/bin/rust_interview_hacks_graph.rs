
#[derive(Debug)]
struct Node {
    value: i32,
    children: Vec<Node>,
}


fn visit_iter(root: &Node) {
    let mut stack = Vec::<&Node>::from([root]);

    while let Some(node) = stack.pop() {
        println!("{:?}", node);
        // Idiomatic and concise way to extend stack with neighbour iterator
        stack.extend(node.children.iter());
    }
}

fn main() {
    let tree = Node {
        value: 1,
        children: vec![
            Node { value: 2, children: vec![] },
            Node {
                value: 3,
                children: vec![Node { value: 4, children: vec![] }],
            },
        ],
    };

    visit_iter(&tree);
    println!("still own it: {}", tree.value); // tree wasn't moved
}

