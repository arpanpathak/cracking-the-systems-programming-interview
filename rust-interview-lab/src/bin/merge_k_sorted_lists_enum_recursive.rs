pub type NodeLink = Box<ListNode>;

#[derive(Debug, PartialEq, Eq, Default)]
pub enum ListNode {
    #[default]
    Empty,
    Node(i32, NodeLink),
}

impl From<Vec<i32>> for NodeLink {
    fn from(vec: Vec<i32>) -> Self {
        vec.into_iter()
            .rev()
            .fold(NodeLink::default(), |acc, v| {
                NodeLink::new(ListNode::Node(v, acc))
            })
    }
}

impl From<Vec<i32>> for ListNode {
    fn from(vec: Vec<i32>) -> Self {
        *NodeLink::from(vec)
    }
}

impl ListNode {
    pub fn merge_k_lists(mut lists: Vec<NodeLink>) -> NodeLink {
        if lists.is_empty() {
            return NodeLink::default();
        }
        let mut interval = 1;
        while interval < lists.len() {
            for i in (0..lists.len()).step_by(interval * 2) {
                if i + interval < lists.len() {
                    let right = std::mem::take(&mut lists[i + interval]);
                    let left = std::mem::take(&mut lists[i]);
                    lists[i] = NodeLink::new(Self::merge(*left, *right));
                }
            }
            interval *= 2;
        }
        lists.swap_remove(0)
    }

    fn merge(l1: ListNode, l2: ListNode) -> ListNode {
        match (l1, l2) {
            (ListNode::Empty, l) | (l, ListNode::Empty) => l,
            (ListNode::Node(v1, n1), ListNode::Node(v2, n2)) => {
                if v1 <= v2 {
                    let rest = Self::merge(*n1, ListNode::Node(v2, n2));
                    ListNode::Node(v1, NodeLink::new(rest))
                } else {
                    let rest = Self::merge(ListNode::Node(v1, n1), *n2);
                    ListNode::Node(v2, NodeLink::new(rest))
                }
            }
        }
    }
}

fn main() {
    let lists: Vec<NodeLink> = vec![
        vec![1, 4, 5].into(),
        vec![1, 3, 4].into(),
        vec![2, 6].into(),
    ];

    let merged = ListNode::merge_k_lists(lists);

    println!("{:#?}", merged);
}
