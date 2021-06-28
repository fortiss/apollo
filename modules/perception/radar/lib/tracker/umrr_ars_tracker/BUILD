load("//tools:cpplint.bzl", "cpplint")

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "umrr_ars_tracker",
    srcs = [
        "umrr_ars_tracker.cc",
    ],
    hdrs = [
        "umrr_ars_tracker.h",
    ],
    deps = [
        "//modules/perception/base",
        "//modules/perception/common/graph",
        "//modules/perception/lib/config_manager",
        "//modules/perception/lib/registerer",
        "//modules/perception/proto:perception_config_schema_proto",
        "//modules/perception/radar/common:types",
        "//modules/perception/radar/lib/interface:base_matcher",
        "//modules/perception/radar/lib/interface:base_tracker",
        "//modules/perception/radar/lib/tracker/common:radar_track_manager",
        "//modules/perception/radar/lib/tracker/matcher:hm_matcher",
        "@eigen",
    ],
)

cpplint()
