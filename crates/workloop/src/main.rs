//! Binary entrypoint for `workloop`.

use std::io::{self, Write};
use std::process::ExitCode;

fn main() -> ExitCode {
    let outcome = workloop::run(std::env::args_os());
    if !outcome.stdout.is_empty() {
        let _ = io::stdout().write_all(outcome.stdout.as_bytes());
    }
    if !outcome.stderr.is_empty() {
        let _ = io::stderr().write_all(outcome.stderr.as_bytes());
    }
    ExitCode::from(outcome.exit_code)
}
