#[derive(Debug)]
#[allow(dead_code)] // But DreamON
enum Situation {
    UnderControl,
    GracePeriod,
    OutOfStatus,
}

fn main() {
    let visa_situation = Situation::GracePeriod;
    let fear_mongers_bothering = true;

    match (visa_situation, fear_mongers_bothering) {
        (Situation::UnderControl, _) => {
            println!("Good for you, good for you, I hope Murphy's law isn't true. Or is it? J.K jk");
        }
        (Situation::GracePeriod, true) => {
            println!(
                "Just leave, and come back with consular processing mate! Use your brain cells, \
                 even the Federal Register requires 60 days public review for comments \
                 (kinda like an RFC, innit?)."
            );
        }
        (Situation::GracePeriod, false) => {
            println!("Grace period, and nobody's bothering you. Breathe. Touch grass, study and chill.");
        }
        (Situation::OutOfStatus, _) => {
            println!("Hold on, don't be scared, destiny will keep you up, stop crying your heart out");
        }
    }
}
