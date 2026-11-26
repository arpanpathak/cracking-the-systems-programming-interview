//! An 8x8 board of queens where no queen may attack another, tracked with bitmasks.
//!
//! Each row, column, diagonal and anti-diagonal is one bit. A square is free for a
//! queen when none of its four lines is taken. A queen that blocks a move always sits
//! on a line through the destination, so the same check also stops queens jumping
//! over each other.

#[derive(Debug)]
enum Error {
    InvalidMove(&'static str),
    OutOfBounds,
    /// A queen already stands on the square.
    Occupied,
    /// Another queen shares the square's row, column or a diagonal.
    Attacked,
    /// There is no queen on the square to move.
    EmptySquare,
}

impl std::fmt::Display for Error {
    fn fmt(&self, formatter: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Error::InvalidMove(reason) => write!(formatter, "invalid move: {reason}"),
            Error::OutOfBounds => write!(formatter, "square is off the board"),
            Error::Occupied => write!(formatter, "a queen already stands there"),
            Error::Attacked => write!(formatter, "another queen attacks that square"),
            Error::EmptySquare => write!(formatter, "no queen on that square"),
        }
    }
}

impl std::error::Error for Error {}

type Res<T = ()> = Result<T, Error>;

#[derive(Clone, Copy, Debug, PartialEq)]
struct Cell {
    x: usize,
    y: usize,
}

trait Piece {
    fn can_move(&self, from: Cell, to: Cell) -> bool;
}

struct Queen;

impl Piece for Queen {
    fn can_move(&self, from: Cell, to: Cell) -> bool {
        let dx = from.x.abs_diff(to.x);
        let dy = from.y.abs_diff(to.y);

        dx == 0 || dy == 0 || dx == dy
    }
}

struct Chess {
    /// One bit per square that holds a queen: bit `x * 8 + y`.
    squares: u64,
    rows: u8,
    cols: u8,
    diags: u16,
    anti_diags: u16,
}

impl Chess {
    fn new() -> Self {
        Self {
            squares: 0,
            rows: 0,
            cols: 0,
            diags: 0,
            anti_diags: 0,
        }
    }

    fn check_bounds(cell: Cell) -> Res {
        if cell.x >= 8 || cell.y >= 8 {
            return Err(Error::OutOfBounds);
        }

        Ok(())
    }

    fn square(cell: Cell) -> u64 {
        1u64 << (cell.x * 8 + cell.y)
    }

    /// Adds or removes a queen: XOR sets the five bits when they are clear and
    /// clears them when they are set.
    fn toggle(&mut self, cell: Cell) {
        self.squares ^= Self::square(cell);
        self.rows ^= 1u8 << cell.x;
        self.cols ^= 1u8 << cell.y;
        self.diags ^= 1u16 << (cell.x + 7 - cell.y);
        self.anti_diags ^= 1u16 << (cell.x + cell.y);
    }

    fn place(&mut self, cell: Cell) -> Res {
        Self::check_bounds(cell)?;

        if self.squares & Self::square(cell) != 0 {
            return Err(Error::Occupied);
        }

        let attacked = (self.rows & (1u8 << cell.x)) != 0
            || (self.cols & (1u8 << cell.y)) != 0
            || (self.diags & (1u16 << (cell.x + 7 - cell.y))) != 0
            || (self.anti_diags & (1u16 << (cell.x + cell.y))) != 0;

        if attacked {
            return Err(Error::Attacked);
        }

        self.toggle(cell);

        Ok(())
    }

    fn move_piece(&mut self, piece: &dyn Piece, from: Cell, to: Cell) -> Res {
        Self::check_bounds(from)?;

        if self.squares & Self::square(from) == 0 {
            return Err(Error::EmptySquare);
        }

        if from == to || !piece.can_move(from, to) {
            return Err(Error::InvalidMove("illegal trajectory"));
        }

        // Lift the queen first, or its own row, column and diagonals block every move.
        self.toggle(from);

        let placed = self.place(to);

        if placed.is_err() {
            self.toggle(from); // the move failed: put the queen back
        }

        placed
    }
}

fn main() -> Res {
    let mut board = Chess::new();
    let queen = Queen;

    board.place(Cell { x: 0, y: 0 })?;
    board.place(Cell { x: 1, y: 2 })?;
    println!("placed queens on (0,0) and (1,2)");

    let along_row = board.move_piece(&queen, Cell { x: 0, y: 0 }, Cell { x: 0, y: 5 });
    println!("(0,0) -> (0,5) along its row:        {along_row:?}");

    let knight_jump = board.move_piece(&queen, Cell { x: 1, y: 2 }, Cell { x: 3, y: 3 });
    println!("(1,2) -> (3,3) is a knight's jump:   {knight_jump:?}");

    let into_attack = board.move_piece(&queen, Cell { x: 1, y: 2 }, Cell { x: 1, y: 5 });
    println!("(1,2) -> (1,5) shares column 5:      {into_attack:?}");

    let from_empty = board.move_piece(&queen, Cell { x: 4, y: 4 }, Cell { x: 4, y: 6 });
    println!("(4,4) -> (4,6) from an empty square: {from_empty:?}");

    let off_board = board.place(Cell { x: 8, y: 0 });
    println!("place (8,0):                         {off_board:?}");

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cell(x: usize, y: usize) -> Cell {
        Cell { x, y }
    }

    #[test]
    fn queen_moves_along_its_own_lines() -> Res {
        let mut board = Chess::new();
        board.place(cell(0, 0))?;

        board.move_piece(&Queen, cell(0, 0), cell(0, 5))?; // row
        board.move_piece(&Queen, cell(0, 5), cell(6, 5))?; // column
        board.move_piece(&Queen, cell(6, 5), cell(4, 3))?; // diagonal

        Ok(())
    }

    #[test]
    fn failed_move_leaves_the_queen_in_place() -> Res {
        let mut board = Chess::new();
        board.place(cell(0, 0))?;
        board.place(cell(1, 2))?;

        let blocked = board.move_piece(&Queen, cell(0, 0), cell(0, 2)); // column 2 is taken
        assert!(matches!(blocked, Err(Error::Attacked)));

        // (0,0) still holds its queen, so its lines still block (5,5).
        assert!(matches!(board.place(cell(5, 5)), Err(Error::Attacked)));
        board.move_piece(&Queen, cell(0, 0), cell(0, 7))?;

        Ok(())
    }

    #[test]
    fn rejects_bad_moves() -> Res {
        let mut board = Chess::new();
        board.place(cell(3, 3))?;

        let same_square = board.move_piece(&Queen, cell(3, 3), cell(3, 3));
        let empty_square = board.move_piece(&Queen, cell(5, 0), cell(5, 1));
        let off_board = board.move_piece(&Queen, cell(9, 9), cell(3, 3));
        let occupied = board.place(cell(3, 3));

        assert!(matches!(same_square, Err(Error::InvalidMove(_))));
        assert!(matches!(empty_square, Err(Error::EmptySquare)));
        assert!(matches!(off_board, Err(Error::OutOfBounds)));
        assert!(matches!(occupied, Err(Error::Occupied)));

        Ok(())
    }
}
