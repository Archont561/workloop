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

  Scenario: Two loops never claim the same backlog task
    Given a temporary backlog with two unclaimed task cards
    When two task claims run at the same time
    Then the task claimer hands each loop a different card
    And both claimed cards are marked In Progress

  Scenario: Every Pixi task named in agent instructions exists
    Given the live workloop repository workspace
    When the documented-task guard inspects the workspace
    Then the documented-task guard reports zero missing tasks

  Scenario: Every release destination and platform is one the workflow builds
    Given the live workloop repository workspace
    When the distribution guard inspects the workspace
    Then the distribution guard reports zero problems

  Scenario: Reject a release workflow that publishes to crates.io
    Given a temporary workspace whose release workflow runs "cargo publish"
    When the distribution guard inspects that temporary workspace
    Then the distribution guard reports a crates.io publication violation

  Scenario: Reject a Pixi packaging platform the release matrix never builds
    Given a temporary workspace whose packaging platforms include "win-64"
    When the distribution guard inspects that temporary workspace
    Then the distribution guard reports a platform mismatch

  Scenario: Reject a skill edited without updating its locked hash
    Given a temporary workspace with one locked skill
    When the skill folder is edited but skills-lock.json is not
    Then the skills guard reports drift for that skill
    And rehashing the lock clears the drift

  Scenario: Reject a workspace with no release workflow
    Given a temporary workspace with no release workflow
    When the distribution guard inspects that temporary workspace
    Then the distribution guard reports the missing workflow

  Scenario: Reject a release matrix with no platforms
    Given a temporary workspace whose release matrix declares no platforms
    When the distribution guard inspects that temporary workspace
    Then the distribution guard reports an empty release matrix

  Scenario Outline: Reject a recipe that disagrees with the release matrix
    Given a temporary workspace whose recipe pins "<marker>" for a "<platform>" target
    When the distribution guard inspects that temporary workspace
    Then the distribution guard reports a recipe mismatch for "<platform>"

    Examples:
      | marker            | platform     |
      | win               | win-64       |
      | osx and x86_64    | osx-64       |
      | linux and aarch64 | linux-aarch64 |

  Scenario: Reject a shipped platform with no variant pin
    Given a temporary workspace whose recipe omits the variant pin for osx-arm64
    When the distribution guard inspects that temporary workspace
    Then the distribution guard reports a missing variant pin

  Scenario: Accept a minimal workspace that declares no Pixi packaging or recipe
    Given a temporary workspace with only a release workflow
    When the distribution guard inspects that temporary workspace
    Then the distribution guard reports zero problems
