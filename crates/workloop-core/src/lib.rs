//! Core library for `workloop`.
//!
//! At this initial scaffold stage (`0.1.0`), `workloop-core` exposes only
//! package version metadata. Lifecycle state, free-model pool routing, and
//! review gates tracked in `backlog/` will live here cleanly separated from CLI
//! presentation concerns.

/// Semantic version of `workloop-core`, sourced from `Cargo.toml`.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Crate identifier for `workloop-core`.
pub const CRATE_NAME: &str = env!("CARGO_PKG_NAME");

/// Formats the canonical human-readable version banner (`workloop <semver>`).
#[must_use]
pub fn version_banner() -> String {
    format!("workloop {VERSION}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_banner_prefixes_binary_name() {
        assert_eq!(version_banner(), format!("workloop {VERSION}"));
        assert_eq!(CRATE_NAME, "workloop-core");
    }
}
