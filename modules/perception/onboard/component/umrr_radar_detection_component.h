/******************************************************************************

fortiss

adapted from apollos radar node!

 *****************************************************************************/
#pragma once

#include <memory>
#include <string>
#include <vector>

#include "cyber/component/component.h"
#include "modules/localization/proto/localization.pb.h"
#include "modules/perception/base/sensor_meta.h"
#include "modules/perception/lib/utils/time_util.h"
#include "modules/perception/map/hdmap/hdmap_input.h"
#include "modules/perception/onboard/common_flags/common_flags.h"
#include "modules/perception/onboard/inner_component_messages/inner_component_messages.h"
#include "modules/perception/onboard/msg_buffer/msg_buffer.h"
#include "modules/perception/onboard/proto/umrr_radar_component_config.pb.h"
#include "modules/perception/onboard/transform_wrapper/transform_wrapper.h"
#include "modules/canbus/proto/chassis_detail.pb.h"

namespace apollo {
namespace perception {
namespace onboard {

struct RawRadarDetections {
  double x;
  double y;
  double v;
  int id;
};

using ::apollo::canbus::ChassisDetail;
using ::apollo::localization::LocalizationEstimate;

class UmrrRadarDetectionComponent : public cyber::Component<ChassisDetail> {
  
 public:
  UmrrRadarDetectionComponent()
      : seq_num_(0),
        tf_child_frame_id_(""),
        odometry_channel_name_(""),
        hdmap_input_(nullptr) {}
  ~UmrrRadarDetectionComponent() = default;

  bool Init() override;
  bool Proc(const std::shared_ptr<ChassisDetail>& message) override;

 private:

  bool InternalProc(const std::shared_ptr<ChassisDetail>& in_message,
                    std::shared_ptr<SensorFrameMessage> out_message);
  //bool GetCarLocalizationSpeed(double timestamp,
  //                             Eigen::Vector3f* car_linear_speed,
  //                             Eigen::Vector3f* car_angular_speed);

  UmrrRadarDetectionComponent(const UmrrRadarDetectionComponent&) = delete;
  UmrrRadarDetectionComponent& operator=(const UmrrRadarDetectionComponent&) = delete;

 private:

  bool GetRawRadarData(const std::shared_ptr<ChassisDetail>& in_message, const double& chassis_detail_time);

  bool GetLocalizationAndTransform(
    const bool& chassis_detail_has_time,
    const double& chassis_detail_time,
    std::shared_ptr<SensorFrameMessage>& out_message, 
    std::shared_ptr<LocalizationEstimate const>& loct_ptr, 
    Eigen::Affine3d& radar_trans);

  bool FillSensorFrameMessage(
    std::shared_ptr<SensorFrameMessage>& out_message,
    const Eigen::Affine3d& radar_trans,
    const std::shared_ptr<LocalizationEstimate const>& loct_ptr,
    const double& chassis_detail_time);

  template<class UmrrRadarCanFrame>
  void ProcessFrontObject(const UmrrRadarCanFrame obj);

  template<class UmrrRadarCanFrame>
  void ProcessRearObject(const UmrrRadarCanFrame obj);

  UmrrRadarComponentConfig comp_config_;

  uint32_t seq_num_;

  base::SensorInfo radar_info_;
  std::string tf_child_frame_id_;
  std::string odometry_channel_name_;

  TransformWrapper radar2world_trans_;
  TransformWrapper radar2imar_trans_;
  map::HDMapInput* hdmap_input_;
  MsgBuffer<LocalizationEstimate> localization_subscriber_;
  std::shared_ptr<apollo::cyber::Writer<SensorFrameMessage>> writer_;

  std::vector<RawRadarDetections> raw_radar_detections_;
};

CYBER_REGISTER_COMPONENT(UmrrRadarDetectionComponent);

}  // namespace onboard
}  // namespace perception
}  // namespace apollo
