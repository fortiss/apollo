load("//tools:cpplint.bzl", "cpplint")

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "devkit_vehicle_factory",
    srcs = [
        "devkit_vehicle_factory.cc",
    ],
    hdrs = [
        "devkit_vehicle_factory.h",
    ],
    deps = [
        ":devkit_controller",
        ":devkit_message_manager",
        "//modules/canbus/vehicle:abstract_vehicle_factory",
    ],
)

cc_test(
    name = "devkit_vehicle_factory_test",
    size = "small",
    srcs = ["devkit_vehicle_factory_test.cc"],
    deps = [
        ":devkit_vehicle_factory",
        "@gtest//:main",
    ],
)

cc_library(
    name = "devkit_message_manager",
    srcs = [
        "devkit_message_manager.cc",
    ],
    hdrs = [
        "devkit_message_manager.h",
    ],
    deps = [
        "//modules/drivers/canbus/common:canbus_common",
        "//modules/canbus/proto:canbus_proto",
        "//modules/drivers/canbus/can_comm:message_manager_base",
        "//modules/canbus/vehicle/devkit/protocol:canbus_devkit_protocol",
    ],
)

cc_test(
    name = "devkit_message_manager_test",
    size = "small",
    srcs = ["devkit_message_manager_test.cc"],
    deps = [
        "//modules/canbus/vehicle/devkit:devkit_message_manager",
        "@gtest//:main",
    ],
)

cc_library(
    name = "devkit_controller",
    srcs = [
        "devkit_controller.cc",
    ],
    hdrs = [
        "devkit_controller.h",
    ],
    deps = [
        ":devkit_message_manager",
        "//modules/canbus/common:canbus_common",
        "//modules/drivers/canbus/can_comm:can_sender",
        "//modules/drivers/canbus/common:canbus_common",
        "//modules/canbus/proto:canbus_proto",
        "//modules/drivers/canbus/can_comm:message_manager_base",
        "//modules/canbus/vehicle:vehicle_controller_base",
        "//modules/canbus/vehicle/devkit/protocol:canbus_devkit_protocol",
    ],
)

cc_test(
    name = "devkit_controller_test",
    size = "small",
    srcs = ["devkit_controller_test.cc"],
    data = ["//modules/canbus:canbus_testdata"],
    deps = [
        ":devkit_controller",
        "@gtest//:main",
    ],
)

cpplint()
