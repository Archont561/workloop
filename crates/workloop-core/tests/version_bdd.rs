use std::cell::RefCell;

use rstest::fixture;
use rstest_bdd_macros::{given, scenario, then, when};

#[derive(Default)]
struct CoreWorld {
    banner: RefCell<String>,
}

#[fixture]
fn world() -> CoreWorld {
    CoreWorld::default()
}

#[given("the workloop-core library is loaded")]
fn library_loaded(world: &CoreWorld) {
    let _ = world;
    assert_eq!(workloop_core::CRATE_NAME, "workloop-core");
}

#[when("I format the version banner")]
fn format_banner(world: &CoreWorld) {
    *world.banner.borrow_mut() = workloop_core::version_banner();
}

#[then("the banner starts with \"workloop \" followed by a non-empty semver")]
fn banner_matches_semver(world: &CoreWorld) {
    let banner = world.banner.borrow();
    let rest = banner
        .strip_prefix("workloop ")
        .expect("banner must start with 'workloop '");
    assert!(!rest.is_empty(), "semver portion must not be empty");
    assert_eq!(rest, workloop_core::VERSION);
}

#[scenario(path = "features/core_version.feature")]
fn core_version_banner(world: CoreWorld) {
    let _ = world;
}
