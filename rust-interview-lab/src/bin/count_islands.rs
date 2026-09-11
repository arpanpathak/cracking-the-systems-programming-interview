// ============================================================================
// Count Islands
//
// Ported from the Rust playground repo.
//
// Problem: given a grid of cells, count the number of connected "land"
// regions. Two land cells are connected when they are adjacent horizontally
// or vertically (4-directional). Water cells are not traversable.
//
// Why this appears in cloud interviews:
//   - "Islands" are connected-component counting, the same shape used to find
//     connected GPU nodes, failure domains, network partitions, or storage
//     groups in distributed systems.
//   - The generic implementation accepts any land type (char, u8, bool) and
//     uses BFS with an explicit visited set, which is easy to reason about.
//
// Time complexity: O(rows * cols)
// Space complexity: O(rows * cols) for the visited set and BFS queue.
// ============================================================================

use std::collections::{HashSet, VecDeque};

/// Counts 4-directionally connected components of `land` in a rectangular grid.
///
/// The grid is generic over cell values so callers can use `'1'/'0'`,
/// `true/false`, `1u8/0u8`, or any other PartialEq value.
fn count_islands<T: PartialEq>(grid: &[&[T]], land: T) -> usize {
    if grid.is_empty() || grid[0].is_empty() {
        return 0;
    }

    let rows = grid.len();
    let cols = grid[0].len();
    let mut visited = HashSet::new();
    let mut count = 0;
    let dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)];

    // BFS closure: flood-fill one island starting from a known land cell.
    // Passing `visited` explicitly avoids borrow-checker friction when calling
    // the closure from the outer loop.
    let bfs = |start: (usize, usize), visited: &mut HashSet<(usize, usize)>| {
        let mut queue = VecDeque::new();
        queue.push_back(start);
        visited.insert(start);

        while let Some((cr, cc)) = queue.pop_front() {
            for &(dr, dc) in &dirs {
                let nr = cr as i32 + dr;
                let nc = cc as i32 + dc;

                if (0..rows as i32).contains(&nr) && (0..cols as i32).contains(&nc) {
                    let (ur, uc) = (nr as usize, nc as usize);
                    if grid[ur][uc] == land && !visited.contains(&(ur, uc)) {
                        visited.insert((ur, uc));
                        queue.push_back((ur, uc));
                    }
                }
            }
        }
    };

    for r in 0..rows {
        for c in 0..cols {
            if grid[r][c] == land && !visited.contains(&(r, c)) {
                count += 1;
                bfs((r, c), &mut visited);
            }
        }
    }

    count
}

// ============================================================================
// Runnable demonstration
// ============================================================================
fn main() {
    let grid = [
        &['1', '1', '0', '0', '0'][..],
        &['1', '1', '0', '0', '0'][..],
        &['0', '0', '1', '0', '0'][..],
        &['0', '0', '0', '1', '1'][..],
    ];

    println!("Islands: {}", count_islands(&grid, '1'));

    let boolean_grid = [
        &[true, true, false][..],
        &[false, false, false][..],
        &[false, true, true][..],
    ];
    println!("Boolean islands: {}", count_islands(&boolean_grid, true));
}

// ============================================================================
// Tests (cargo test --bin count_islands)
// ============================================================================
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_grid_has_zero_islands() {
        let empty: [&[char]; 0] = [];
        assert_eq!(count_islands(&empty, '1'), 0);

        let no_cols: [&[char]; 2] = [&[], &[]];
        assert_eq!(count_islands(&no_cols, '1'), 0);
    }

    #[test]
    fn counts_classic_example() {
        let grid = [
            &['1', '1', '0', '0', '0'][..],
            &['1', '1', '0', '0', '0'][..],
            &['0', '0', '1', '0', '0'][..],
            &['0', '0', '0', '1', '1'][..],
        ];
        assert_eq!(count_islands(&grid, '1'), 3);
    }

    #[test]
    fn all_water_is_zero() {
        let grid = [&['0', '0'][..], &['0', '0'][..]];
        assert_eq!(count_islands(&grid, '1'), 0);
    }

    #[test]
    fn generic_bool_grid_works() {
        let grid = [
            &[true, false, false][..],
            &[true, false, true][..],
            &[false, false, true][..],
        ];
        assert_eq!(count_islands(&grid, true), 2);
    }

    #[test]
    fn single_row_and_column() {
        let row = [&['1', '0', '1', '1'][..]];
        assert_eq!(count_islands(&row, '1'), 2);

        let col = [&['1'][..], &['1'][..], &['0'][..], &['1'][..]];
        assert_eq!(count_islands(&col, '1'), 2);
    }
}
