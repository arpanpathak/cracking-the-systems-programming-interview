#[derive(Debug)]
enum Error {
    InvalidMove(&'static str),
    OutOfBounds,
    Occupied,
}

type Res<T = ()> = Result<T, Error>;

#[derive(Clone, Copy, Debug)]
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

#[derive(Clone, Copy)]
struct Chess {
    rows: u8,
    cols: u8,
    diags: u16,
    anti_diags: u16,
}

impl Chess {
    fn new() -> Self {
        Self {
            rows: 0,
            cols: 0,
            diags: 0,
            anti_diags: 0,
        }
    }

    fn place(&mut self, cell: Cell) -> Res {
        if cell.x >= 8 || cell.y >= 8 {
            return Err(Error::OutOfBounds);
        }

        let r = 1u8 << cell.x;
        let c = 1u8 << cell.y;
        let d = 1u16 << (cell.x + 7 - cell.y);
        let ad = 1u16 << (cell.x + cell.y);

        if (self.rows & r) != 0
            || (self.cols & c) != 0
            || (self.diags & d) != 0
            || (self.anti_diags & ad) != 0
        {
            return Err(Error::Occupied);
        }

        self.rows |= r;
        self.cols |= c;
        self.diags |= d;
        self.anti_diags |= ad;

        Ok(())
    }

    fn remove(&mut self, cell: Cell) {
        self.rows &= !(1u8 << cell.x);
        self.cols &= !(1u8 << cell.y);
        self.diags &= !(1u16 << (cell.x + 7 - cell.y));
        self.anti_diags &= !(1u16 << (cell.x + cell.y));
    }

    fn move_piece(&mut self, piece: &dyn Piece, from: Cell, to: Cell) -> Res {
        if !piece.can_move(from, to) {
            return Err(Error::InvalidMove("illegal trajectory"));
        }

        // Lift the queen first: on `from`, its own lines are still marked occupied.
        let before = *self;
        self.remove(from);

        let placed = self.place(to);
        if placed.is_err() {
            *self = before;
        }

        placed
    }
}

fn main() -> Res {
    let mut board = Chess::new();
    let queen = Queen;

    board.place(Cell { x: 0, y: 0 })?;
    board.move_piece(&queen, Cell { x: 0, y: 0 }, Cell { x: 2, y: 2 })?;

    println!("moved the queen from (0, 0) to (2, 2)");
    println!("place (5, 5): {:?}", board.place(Cell { x: 5, y: 5 }));

    Ok(())
}
