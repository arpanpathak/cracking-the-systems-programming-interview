use std::sync::{Arc, Mutex};
use std::thread;

#[derive(Debug, Default)]
struct User {
    name: String,
}

#[derive(Default, Debug)]
struct BankAccount {
    name: String,
    owner: User,
    balance: i128

}

enum Transaction {
    CheckBalance,
    Withdraw,
    Deposit {user: User, balance: i128}
}

fn main() {

    let mut bank_account = BankAccount::default();
    
    let users = [
        User { name: "Arpan".into() },
        User { name: "Adam".into() },
        User { name: "One Rich Asshole Called Larry Elison".into() },
        User { name: "Satyash Nadella".into() },
    ];

    users.iter().map(|user| {
        user.name.clone()
    });

}






