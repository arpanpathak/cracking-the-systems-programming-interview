use std::fs::File;
use std::io::{self, BufRead, BufReader, Seek, SeekFrom};

struct Page {
    jobs: Vec<String>,
    next_cursor: Option<u64> // Byte offset where the next page starts
}

fn read_page(path: &str, cursor: u64, page_size: usize) -> io::Result<Page> {
    let mut file = File::open(path)?;
    file.seek(SeekFrom::Start(cursor))?;
    let mut reader = BufReader::new(file);

    // Optimization which preserves as large as the max mage size
    let mut jobs: Vec<String> = Vec::with_capacity(page_size);
    let mut offset = cursor;
    let mut line = String::new();
    
    while jobs.len() < page_size {
        // Clear the previously read line
        line.clear();

        match reader.read_line(&mut line)? {
            0 => break, 
            bytes_read => { 
                offset += bytes_read as u64; 
                jobs.push(line.trim_end().to_string()); 
            }, 
        }
    }

    let at_end  = reader.fill_buf()?.is_empty();
    let next_cursor = if at_end  { None } else {Some(offset)};

    Ok(Page { jobs, next_cursor})
}

fn main() -> io::Result<()> {
    let mut cursor = 0;

    loop {
        let page = read_page("src/bin/large_file.txt", cursor, 3)?;

        println!("--- page ---");
        for job in &page.jobs {
            println!("{job}");
        }

        match page.next_cursor {
            Some(next) => cursor = next,
            None => break,
        }
    }

    Ok(())
}
