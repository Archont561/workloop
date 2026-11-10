Feature: CLI version and help behavior
  As a developer invoking workloop
  I want predictable version, help, and error exits
  So that shell hooks and orchestrators can verify the installed binary

  Scenario: Display help via flag
    Given the "workloop" command with "--help"
    When it runs
    Then it exits with code 0
    And standard output mentions "Usage: workloop"
    And standard error is empty

  Scenario: Print version via long flag
    Given the "workloop" command with "--version"
    When it runs
    Then it exits with code 0
    And trimmed standard output equals "workloop 0.1.0"
    And standard error is empty

  Scenario: Print version via subcommand
    Given the "workloop" command with "version"
    When it runs
    Then it exits with code 0
    And trimmed standard output equals "workloop 0.1.0"
    And standard error is empty

  Scenario: Reject unknown flag with usage exit code
    Given the "workloop" command with "--unknown-flag"
    When it runs
    Then it exits with code 2
    And standard error mentions "unexpected argument"
