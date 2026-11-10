//! Standalone CLI entrypoint library for `workloop`.
//!
//! At this scaffold stage (`0.1.0`), the CLI supports version and help queries
//! backed by `workloop-core`, plus the `clifacet` command and secret-redaction
//! seam that upcoming lifecycle verbs (`open`, `exec`, `verify`, `close`) build
//! on (decision-2). No interactive frontend feature is enabled yet.

use std::ffi::OsString;

use clap::error::ErrorKind;
use clap::{Arg, ArgAction, Command};

/// Crate version read from `CARGO_PKG_VERSION` at compile time.
///
/// ```
/// assert_eq!(workloop::VERSION, workloop_core::VERSION);
/// ```
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Outcome returned by invoking the CLI parser and dispatcher.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CliOutcome {
    /// Process exit code (`0` for success, `2` for usage errors).
    pub exit_code: u8,
    /// Content written to standard output.
    pub stdout: String,
    /// Content written to standard error.
    pub stderr: String,
}

/// Render `value` the way `clifacet` renders a secret, for anywhere output is built.
///
/// Later lifecycle commands take provider API keys and GitHub App installation
/// tokens as command inputs. `clifacet`'s `Secret` redacts itself in both
/// `Display` and `Debug`, keeping credentials out of logs and failure messages.
///
/// ```
/// let token = workloop::redacted("sk-or-v1-live-secret");
/// assert_eq!(token, "[redacted]");
/// assert!(!token.contains("sk-or-v1-live-secret"));
/// ```
#[must_use]
pub fn redacted(value: &str) -> String {
    clifacet::secret::Secret::new(value.to_owned()).to_string()
}

fn build_cli() -> Command {
    Command::new("workloop")
        .about("Zero-cost AI feature delivery loop for GitHub powered by free open models.")
        .version(VERSION)
        .disable_version_flag(true)
        .arg(
            Arg::new("version")
                .short('V')
                .long("version")
                .action(ArgAction::SetTrue)
                .help("Print version information"),
        )
        .subcommand(Command::new("version").about("Print version information"))
}

/// Parse arguments and produce the CLI stdout, stderr, and exit code without exiting the process.
///
/// ```
/// let outcome = workloop::run(["workloop", "--version"]);
/// assert_eq!(outcome.exit_code, 0);
/// assert_eq!(outcome.stdout.trim(), format!("workloop {}", workloop::VERSION));
/// ```
#[must_use]
pub fn run<I, T>(args: I) -> CliOutcome
where
    I: IntoIterator<Item = T>,
    T: Into<OsString> + Clone,
{
    let mut cmd = build_cli();
    match cmd.try_get_matches_from_mut(args) {
        Ok(matches) => {
            if matches.get_flag("version") || matches.subcommand_name() == Some("version") {
                return CliOutcome {
                    exit_code: 0,
                    stdout: format!("{}\n", workloop_core::version_banner()),
                    stderr: String::new(),
                };
            }
            CliOutcome {
                exit_code: 0,
                stdout: cmd.render_help().to_string(),
                stderr: String::new(),
            }
        }
        Err(error) => {
            let exit_code = match error.kind() {
                ErrorKind::DisplayHelp | ErrorKind::DisplayVersion => 0,
                _ => 2,
            };
            let rendered = error.render().to_string();
            if exit_code == 0 {
                CliOutcome {
                    exit_code: 0,
                    stdout: rendered,
                    stderr: String::new(),
                }
            } else {
                CliOutcome {
                    exit_code,
                    stdout: String::new(),
                    stderr: rendered,
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{VERSION, redacted, run};

    #[test]
    fn version_matches_core_crate() {
        assert_eq!(VERSION, workloop_core::VERSION);
    }

    #[test]
    fn bare_invocation_renders_help_cleanly() {
        let outcome = run(["workloop"]);
        assert_eq!(outcome.exit_code, 0);
        assert!(outcome.stdout.contains("Usage: workloop"));
        assert_eq!(outcome.stderr, "");
    }

    #[test]
    fn help_flag_exits_zero() {
        let outcome = run(["workloop", "--help"]);
        assert_eq!(outcome.exit_code, 0);
        assert!(outcome.stdout.contains("Usage: workloop"));
    }

    #[test]
    fn version_subcommand_matches_flag() {
        let sub = run(["workloop", "version"]);
        let flag = run(["workloop", "--version"]);
        assert_eq!(sub, flag);
    }

    #[test]
    fn credentials_never_reach_rendered_output() {
        let rendered = redacted("sk-or-v1-live-secret");
        assert_eq!(rendered, clifacet::secret::REDACTED);
        assert!(!rendered.contains("sk-or-v1-live-secret"));
    }

    #[test]
    fn unknown_flag_exits_two_on_stderr() {
        let outcome = run(["workloop", "--not-a-flag"]);
        assert_eq!(outcome.exit_code, 2);
        assert_eq!(outcome.stdout, "");
        assert_ne!(outcome.stderr, "");
    }
}
