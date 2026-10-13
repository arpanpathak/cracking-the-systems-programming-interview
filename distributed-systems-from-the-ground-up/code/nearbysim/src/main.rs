//! Command nearbysim finds the drivers nearest to a rider. It compares
//! measuring the distance to every driver with looking only at the square
//! of a grid that the rider is in, and the 8 squares around it.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p nearbysim

// ANCHOR: imports
use std::collections::HashMap;
// ANCHOR_END: imports

// ANCHOR: grid
/// The side of a grid square, in the units of the map. The city is 100
/// units wide, so the grid has 100 by 100 squares.
const SQUARE: f64 = 1.0;

/// A position on the map.
#[derive(Clone, Copy)]
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    /// The square of the grid that the point is in.
    fn square(self) -> (i64, i64) {
        ((self.x / SQUARE) as i64, (self.y / SQUARE) as i64)
    }

    fn distance(self, other: Point) -> f64 {
        ((self.x - other.x).powi(2) + (self.y - other.y).powi(2)).sqrt()
    }
}

/// The drivers of each square.
struct Grid {
    squares: HashMap<(i64, i64), Vec<(usize, Point)>>,
}

impl Grid {
    /// The drivers in the rider's square and the 8 squares around it,
    /// nearest first, and the number of drivers that were looked at.
    fn nearest(&self, rider: Point, count: usize) -> (Vec<(usize, f64)>, usize) {
        let (column, row) = rider.square();
        let mut found: Vec<(usize, f64)> = (-1..=1)
            .flat_map(|dx| (-1..=1).map(move |dy| (column + dx, row + dy)))
            .filter_map(|square| self.squares.get(&square))
            .flatten()
            .map(|&(driver, position)| (driver, rider.distance(position)))
            .collect();
        let looked_at = found.len();

        found.sort_by(|a, b| a.1.total_cmp(&b.1));
        found.truncate(count);

        (found, looked_at)
    }
}
// ANCHOR_END: grid

// ANCHOR: main
/// A repeatable source of positions on a map of 100 by 100 units.
struct Random(u64);

impl Random {
    fn coordinate(&mut self) -> f64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;

        (self.0 % 100_000) as f64 / 1000.0
    }
}

fn main() {
    let mut random = Random(7);
    let drivers: Vec<Point> = std::iter::repeat_with(|| Point {
        x: random.coordinate(),
        y: random.coordinate(),
    })
    .take(20_000)
    .collect();
    let rider = Point { x: 42.5, y: 17.5 };

    let mut all: Vec<(usize, f64)> = drivers
        .iter()
        .enumerate()
        .map(|(driver, &position)| (driver, rider.distance(position)))
        .collect();
    all.sort_by(|a, b| a.1.total_cmp(&b.1));

    let mut grid = Grid {
        squares: HashMap::new(),
    };

    for (driver, &position) in drivers.iter().enumerate() {
        grid.squares
            .entry(position.square())
            .or_default()
            .push((driver, position));
    }

    let (nearest, looked_at) = grid.nearest(rider, 3);
    let describe = |found: &[(usize, f64)]| -> Vec<String> {
        found
            .iter()
            .map(|(driver, distance)| format!("driver {driver} at {distance:.2}"))
            .collect()
    };

    println!("{} drivers on a map of 100 by 100 units", drivers.len());
    println!(
        "measuring every driver: {} distances, nearest: {}",
        all.len(),
        describe(&all[..3]).join(", ")
    );
    println!(
        "using the grid: {looked_at} distances, nearest: {}",
        describe(&nearest).join(", ")
    );
}
// ANCHOR_END: main
