use std::env;

use device_agent_core::render_welcome;

fn main() {
    let color = !env::args().skip(1).any(|arg| arg == "--no-color");
    println!("{}", render_welcome(color));
}
