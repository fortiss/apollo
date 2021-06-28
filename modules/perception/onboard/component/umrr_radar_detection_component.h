/******************************************************************************

fortiss

adapted from apollos radar node!

 *****************************************************************************/
#pragma once

#include <memory>
#include <string>
#include <vector>

#include "cyber/component/component.h"
#include "modules/drivers/proto/umrr_radar_objects.pb.h"
#include "modules/localization/proto/localization.pb.h"
#include "modules/perception/base/sensor_meta.h"
#include "modules/perception/lib/utils/time_util.h"
#include "modules/perception/map/hdmap/hdmap_input.h"
#include "modules/perception/onboard/common_flags/common_flags.h"
#include "modules/perception/onboard/inner_component_messages/inner_component_messages.h"
#include "modules/perception/onboard/msg_buffer/msg_buffer.h"
#include "modules/perception/onboard/proto/umrr_radar_component_config.pb.h"
#include "modules/perception/onboard/transform_wrapper/transform_wrapper.h"
#include "modules/perception/radar/app/umrr_obstacle_perception.h"

namespace apollo {
namespace perception {
namespace onboard {

using apollo::drivers::UmrrRadar;
using apollo::localization::LocalizationEstimate;

class UmrrRadarDetectionComponent : public cyber::Component<UmrrRadar> {
 public:
  UmrrRadarDetectionComponent()
      : seq_num_(0),
        tf_child_frame_id_(""),
        radar_forward_distance_(200.0),
        preprocessor_method_(""),
        perception_method_(""),
        pipeline_name_(""),
        odometry_channel_name_(""),
        hdmap_input_(nullptr),
        radar_preprocessor_(nullptr),
        radar_perception_(nullptr) {}
  ~UmrrRadarDetectionComponent() = default;

  bool Init() override;
  bool Proc(const std::shared_ptr<UmrrRadar>& message) override;

 private:
  bool InitAlgorithmPlugin();
  bool InternalProc(const std::shared_ptr<UmrrRadar>& in_message,
                    std::shared_ptr<SensorFrameMessage> out_message);
  bool GetCarLocalizationSpeed(double timestamp,
                               Eigen::Vector3f* car_linear_speed,
                               Eigen::Vector3f* car_angular_speed);

  UmrrRadarDetectionComponent(const UmrrRadarDetectionComponent&) = delete;
  UmrrRadarDetectionComponent& operator=(const UmrrRadarDetectionComponent&) = delete;

 private:
  std::mutex _mutex;
  uint32_t seq_num_;

  base::SensorInfo radar_info_;
  std::string tf_child_frame_id_;
  double radar_forward_distance_;
  std::string preprocessor_method_;
  std::string perception_method_;
  std::string pipeline_name_;
  std::string odometry_channel_name_;

  TransformWrapper radar2world_trans_;
  TransformWrapper radar2novatel_trans_;
  map::HDMapInput* hdmap_input_;
  std::shared_ptr<radar::UmrrBasePreprocessor> radar_preprocessor_;
  std::shared_ptr<radar::UmrrBaseRadarObstaclePerception> radar_perception_;
  MsgBuffer<LocalizationEstimate> localization_subscriber_;
  std::shared_ptr<apollo::cyber::Writer<SensorFrameMessage>> writer_;
};

CYBER_REGISTER_COMPONENT(UmrrRadarDetectionComponent);

}  // namespace onboard
}  // namespace perception
}  // namespace apollo
