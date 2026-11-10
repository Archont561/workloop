Feature: Core version metadata
  As a consumer of workloop-core
  I want canonical version metadata
  So that every frontend reports an identical semantic version

  Scenario: Version banner matches the package version
    Given the workloop-core library is loaded
    When I format the version banner
    Then the banner starts with "workloop " followed by a non-empty semver
