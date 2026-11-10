Feature: Credential redaction through clifacet
  As a developer passing free-provider API keys and GitHub tokens
  I want credentials redacted whenever output is formatted
  So that secrets never leak into logs or failure output

  Scenario: Redact a live provider API key
    Given a credential value "sk-or-v1-live-token"
    When workloop formats the credential for output
    Then the formatted string equals "[redacted]"
    And the formatted string omits "sk-or-v1-live-token"
