Feature: Repository automation and policy tools

  Python automation tools under tools/ enforce Gherkin hygiene, backlog card
  consistency, free-model registry family separation, and Agent Skills alignment.

  Scenario: Discover and lint every Gherkin feature file in the repository
    Given the live workloop repository workspace
    When the Gherkin linter scans the workspace
    Then the Gherkin linter exits with code 0
    And feature files from both crates and tools are linted

  Scenario: Reject a backlog task marked Done with unchecked acceptance criteria
    Given a temporary backlog directory containing a Done task with an unchecked criterion
    When the backlog status guard validates that directory
    Then the backlog status guard reports at least one problem

  Scenario: Accept a backlog task marked Done when every acceptance criterion is checked
    Given a temporary backlog directory containing a Done task with all criteria checked
    When the backlog status guard validates that directory
    Then the backlog status guard reports zero problems

  Scenario: Validate the free-model registry family and quota separation
    Given the live workloop repository workspace
    When the registry validator inspects the workspace
    Then the registry validator reports zero problems

  Scenario: Reject a free-model registry where implement and review share a family
    Given a temporary registry where implement and review share family "gemini"
    When the registry validator inspects that temporary workspace
    Then the registry validator reports a distinct-family violation

  Scenario: Reject an advisory ignore list cargo-audit cannot parse
    Given a temporary workspace whose audit config carries the unknown "yanked" key
    When the advisory exception guard validates that workspace
    Then the advisory exception guard reports a parse error

  Scenario: Accept an advisory ignore list shared by cargo-deny and cargo-audit
    Given a temporary workspace whose audit config matches deny.toml exactly
    When the advisory exception guard validates that workspace
    Then the advisory exception guard reports zero problems
