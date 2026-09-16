struct ListNode {
    data: u32,
    next: Link,
}

type Link = Option<Box<ListNode>>;

fn merge_k_lists(mut lists: Vec<Link>) -> Link {
    if lists.is_empty() { return None; }

    let (n, mut interval) = (lists.len(), 1);
    while interval < n {
        let mut i = 0;
        while i + interval < n {
            let left = lists[i].take();
            let right = lists[i + interval].take();
            lists[i] = merge_two(left, right);
            i += interval * 2;
        }
        interval *= 2;
    }

    lists[0].take()
}

fn merge_two(mut left: Link, mut right: Link) -> Link {
    let mut merged = None;
    let mut tail = &mut merged;

    while let (Some(l), Some(r)) = (&left, &right) {
        if r.data < l.data {
            std::mem::swap(&mut left, &mut right);
        }
        *tail = left;                              // hang left list on the tail
        tail = &mut tail.as_mut().unwrap().next;   // step past its first node
        left = tail.take();                        // cut the rest off again
    }

    *tail = left.or(right);
    merged
}

fn from_slice(values: &[u32]) -> Link {
    let mut head = None;
    for &data in values.iter().rev() {
        head = Some(Box::new(ListNode { data, next: head }));
    }
    head
}

fn to_vec(mut list: &Link) -> Vec<u32> {
    let mut values = Vec::new();
    while let Some(node) = list {
        values.push(node.data);
        list = &node.next;
    }
    values
}

fn main() {
    let lists = vec![from_slice(&[1, 4, 5]), from_slice(&[1, 3, 4]), from_slice(&[2, 6])];
    println!("{:?}", to_vec(&merge_k_lists(lists)));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merges_three_lists() {
        let lists = vec![from_slice(&[1, 4, 5]), from_slice(&[1, 3, 4]), from_slice(&[2, 6])];
        assert_eq!(to_vec(&merge_k_lists(lists)), vec![1, 1, 2, 3, 4, 4, 5, 6]);
    }

    #[test]
    fn handles_empty_input_and_empty_lists() {
        assert!(merge_k_lists(vec![]).is_none());
        let merged = merge_k_lists(vec![None, from_slice(&[2]), None]);
        assert_eq!(to_vec(&merged), vec![2]);
    }

    #[test]
    fn handles_an_odd_number_of_lists() {
        let lists: Vec<_> = (0..5).map(|i| from_slice(&[i, i + 10])).collect();
        assert_eq!(to_vec(&merge_k_lists(lists)), vec![0, 1, 2, 3, 4, 10, 11, 12, 13, 14]);
    }
}
