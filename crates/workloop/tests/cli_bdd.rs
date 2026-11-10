use assert_cmd::cargo::cargo_bin_cmd;
use rstest::fixture;
use rstest_bdd_macros::{given, scenario, then, when};

#[derive(Default)]
struct CliWorld {
    binary: String,
    arg: String,
    status: Option<i32>,
    stdout: String,
    stderr: String,
    token: String,
    rendered: String,
}

#[fixture]
fn world() -> CliWorld {
    CliWorld::default()
}

#[given("the \"{binary}\" command with \"{arg}\"")]
fn given_command_with_arg(world: &mut CliWorld, binary: String, arg: String) {
    world.binary = binary;
    world.arg = arg;
}

#[when("it runs")]
fn run_command(world: &mut CliWorld) {
    assert_eq!(world.binary, "workloop");
    let output = cargo_bin_cmd!("workloop")
        .arg(&world.arg)
        .output()
        .expect("compiled workloop binary should execute");
    world.status = output.status.code();
    world.stdout = String::from_utf8(output.stdout).expect("stdout must be UTF-8");
    world.stderr = String::from_utf8(output.stderr).expect("stderr must be UTF-8");
}

#[then("it exits with code {code:i32}")]
fn check_exit_code(world: &CliWorld, code: i32) {
    assert_eq!(world.status, Some(code));
}

#[then("standard output mentions \"{expected}\"")]
fn check_stdout_contains(world: &CliWorld, expected: String) {
    assert!(
        world.stdout.contains(&expected),
        "expected stdout to contain {expected:?}, got {:?}",
        world.stdout
    );
}

#[then("trimmed standard output equals \"{expected}\"")]
fn check_stdout_trimmed(world: &CliWorld, expected: String) {
    assert_eq!(world.stdout.trim(), expected);
}

#[then("standard error is empty")]
fn check_stderr_empty(world: &CliWorld) {
    assert_eq!(world.stderr, "");
}

#[then("standard error mentions \"{expected}\"")]
fn check_stderr_contains(world: &CliWorld, expected: String) {
    assert!(
        world.stderr.contains(&expected),
        "expected stderr to contain {expected:?}, got {:?}",
        world.stderr
    );
}

#[given("a credential value \"{token}\"")]
fn given_credential(world: &mut CliWorld, token: String) {
    world.token = token;
}

#[when("workloop formats the credential for output")]
fn format_credential(world: &mut CliWorld) {
    world.rendered = workloop::redacted(&world.token);
}

#[then("the formatted string equals \"{expected}\"")]
fn check_rendered_equals(world: &CliWorld, expected: String) {
    assert_eq!(world.rendered, expected);
}

#[then("the formatted string omits \"{secret}\"")]
fn check_rendered_omits(world: &CliWorld, secret: String) {
    assert!(!world.rendered.contains(&secret));
}

#[scenario(path = "features/cli_version.feature", name = "Display help via flag")]
fn display_help_flag(world: CliWorld) {
    let _ = world;
}

#[scenario(
    path = "features/cli_version.feature",
    name = "Print version via long flag"
)]
fn print_version_long_flag(world: CliWorld) {
    let _ = world;
}

#[scenario(
    path = "features/cli_version.feature",
    name = "Print version via subcommand"
)]
fn print_version_subcommand(world: CliWorld) {
    let _ = world;
}

#[scenario(
    path = "features/cli_version.feature",
    name = "Reject unknown flag with usage exit code"
)]
fn reject_unknown_flag(world: CliWorld) {
    let _ = world;
}

#[scenario(
    path = "features/cli_secret.feature",
    name = "Redact a live provider API key"
)]
fn redact_live_provider_api_key(world: CliWorld) {
    let _ = world;
}
