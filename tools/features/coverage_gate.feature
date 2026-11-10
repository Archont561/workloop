Feature: Rust LCOV coverage threshold gate

  The coverage gate enforces at least 90 percent line coverage across both
  workloop-core and workloop source files before a task or pull request passes.

  Scenario: Accept an LCOV report at or above the 90 percent threshold
    Given a temporary LCOV report with 19 of 20 source lines covered across both crates
    When the coverage gate runs with threshold 90.0
    Then the coverage gate exits with code 0

  Scenario: Reject an LCOV report below the 90 percent threshold
    Given a temporary LCOV report with 14 of 20 source lines covered across both crates
    When the coverage gate runs with threshold 90.0
    Then the coverage gate exits with code 1
