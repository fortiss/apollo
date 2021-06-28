load("//tools:cpplint.bzl", "cpplint")

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "umrr_ars_detector",
    srcs = [
        "umrr_ars_detector.cc",
    ],
    hdrs = [
        "umrr_ars_detector.h",
    ],
    deps = [
        "//modules/drivers/proto:sensor_proto",
        "//modules/perception/base",
        "//modules/perception/common/geometry:roi_filter",
        "//modules/perception/lib/config_manager",
        "//modules/perception/lib/registerer",
        "//modules/perception/proto:perception_config_schema_proto",
        "//modules/perception/radar/common:radar_util",
        "//modules/perception/radar/common:types",
        "//modules/perception/radar/lib/interface:umrr_base_detector",
        "@eigen",
    ],
)

cpplint()
