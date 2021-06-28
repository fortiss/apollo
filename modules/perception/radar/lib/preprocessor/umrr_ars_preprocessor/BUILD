load("//tools:cpplint.bzl", "cpplint")

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "umrr_ars_preprocessor",
    srcs = [
        "umrr_ars_preprocessor.cc",
    ],
    hdrs = [
        "umrr_ars_preprocessor.h",
    ],
    deps = [
        "//modules/drivers/proto:sensor_proto",
        "//modules/perception/base",
        "//modules/perception/lib/config_manager",
        "//modules/perception/lib/registerer",
        "//modules/perception/lib/utils",
        "//modules/perception/radar/common:types",
        "//modules/perception/radar/lib/interface:umrr_base_preprocessor",
        "@eigen",
    ],
)

cpplint()
