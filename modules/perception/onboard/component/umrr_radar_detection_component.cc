/******************************************************************************

fortiss

adapted from apollos radar node!

 *****************************************************************************/
#include "modules/perception/onboard/component/umrr_radar_detection_component.h"
#include "modules/perception/common/sensor_manager/sensor_manager.h"
#include "modules/perception/lib/utils/perf.h"
#include "modules/perception/radar/lib/interface/base_radar_obstacle_perception.h"
#include "modules/perception/radar/common/radar_util.h"

#include "modules/canbus/proto/fortuna.pb.h"

namespace apollo {
namespace perception {
namespace onboard {

bool UmrrRadarDetectionComponent::Init() {
  if (!GetProtoConfig(&comp_config_)) {
    return false;
  }

  // configuration file is in modules/perception/production/conf/perception/umrr_radar/umrr_radar_component_conf_xx.pb.txt
  AINFO << "Radar Component Configs: " << comp_config_.DebugString();

  radar_info_.name = comp_config_.radar_name();
  radar_info_.type = apollo::perception::base::SensorType::LONG_RANGE_RADAR;
  radar_info_.orientation = apollo::perception::base::SensorOrientation::PANORAMIC;
  radar_info_.frame_id = comp_config_.tf_child_frame_id();

  // load component configs
  tf_child_frame_id_ = comp_config_.tf_child_frame_id();
  odometry_channel_name_ = comp_config_.odometry_channel_name();

  writer_ = node_->CreateWriter<SensorFrameMessage>(
      comp_config_.output_channel_name());

  radar2world_trans_.Init(tf_child_frame_id_); 
  radar2imar_trans_.Init(tf_child_frame_id_);
  localization_subscriber_.Init(
      odometry_channel_name_,
      odometry_channel_name_ + '_' + comp_config_.radar_name());
  return true;
}

bool UmrrRadarDetectionComponent::Proc(const std::shared_ptr<ChassisDetail>& message) {
  //!Todo add header to chassis_detail?
  AINFO << "Enter fortuna radar process node at current timestamp " << lib::TimeUtil::GetCurrentTime();
  std::shared_ptr<SensorFrameMessage> out_message(new (std::nothrow) SensorFrameMessage);
  if (!InternalProc(message, out_message)) {
    return false;
  }
  writer_->Write(out_message);
  AINFO << "Send radar processing output message.";
  return true;
}

bool UmrrRadarDetectionComponent::InternalProc(
    const std::shared_ptr<ChassisDetail>& in_message,
    std::shared_ptr<SensorFrameMessage> out_message) {
  
  double chassis_detail_time;
  if(in_message->has_timestamp()) {
    chassis_detail_time = in_message->timestamp();
  } else {
    //This is a hack that works if no latencies are in the system
    chassis_detail_time = lib::TimeUtil::GetCurrentTime();
  }

  GetRawRadarData(in_message, chassis_detail_time); // fills raw_radar_detections_

  if(!raw_radar_detections_.empty()) {
    std::shared_ptr<LocalizationEstimate const> loct_ptr;
    Eigen::Affine3d radar_trans;
    if(!GetLocalizationAndTransform(in_message->has_timestamp(), chassis_detail_time, out_message, loct_ptr, radar_trans)) {
      return false;
    }

    // TODO: Add the ROI filter here?

    if(!FillSensorFrameMessage(out_message, radar_trans, loct_ptr, chassis_detail_time)) {
      return false;
    }
  } 

  out_message->error_code_ = apollo::common::ErrorCode::OK;
  seq_num_ += 1;
  return true;
}
/*
bool UmrrRadarDetectionComponent::GetCarLocalizationSpeed(
    double timestamp, Eigen::Vector3f* car_linear_speed,
    Eigen::Vector3f* car_angular_speed) {
  CHECK_NOTNULL(car_linear_speed);
  (*car_linear_speed) = Eigen::Vector3f::Zero();
  CHECK_NOTNULL(car_angular_speed);
  (*car_angular_speed) = Eigen::Vector3f::Zero();
  std::shared_ptr<LocalizationEstimate const> loct_ptr;
  if (!localization_subscriber_.LookupNearest(timestamp, &loct_ptr)) {
    AERROR << "Cannot get car speed.";
    return false;
  }
  (*car_linear_speed)[0] =
      static_cast<float>(loct_ptr->pose().linear_velocity().x());
  (*car_linear_speed)[1] =
      static_cast<float>(loct_ptr->pose().linear_velocity().y());
  (*car_linear_speed)[2] =
      static_cast<float>(loct_ptr->pose().linear_velocity().z());
  (*car_angular_speed)[0] =
      static_cast<float>(loct_ptr->pose().angular_velocity().x());
  (*car_angular_speed)[1] =
      static_cast<float>(loct_ptr->pose().angular_velocity().y());
  (*car_angular_speed)[2] =
      static_cast<float>(loct_ptr->pose().angular_velocity().z());

  return true;
}
*/

bool UmrrRadarDetectionComponent::FillSensorFrameMessage(
  std::shared_ptr<SensorFrameMessage>& out_message,
  const Eigen::Affine3d& radar_trans,
  const std::shared_ptr<LocalizationEstimate const>& loct_ptr,
  const double& chassis_detail_time) {

    // Fill output msg general fields
    out_message->frame_.reset(new base::Frame());
    out_message->frame_->sensor_info = radar_info_;
    out_message->frame_->timestamp = chassis_detail_time;
    out_message->frame_->sensor2world_pose = radar_trans;
    out_message->timestamp_ = chassis_detail_time;
    out_message->seq_num_ = seq_num_;
    out_message->process_stage_ = ProcessStage::LONG_RANGE_RADAR_DETECTION;
    out_message->sensor_id_ = radar_info_.name;

    // Default values for non-available fields
    const float dummy_confidence = comp_config_.dummy_confidence();
    const float dummy_uncertainty = comp_config_.dummy_uncertainty();
    const float dummy_object_length = comp_config_.dummy_object_length();
    const float dummy_object_width = comp_config_.dummy_object_width();
    const float dummy_object_height = comp_config_.dummy_object_height();
    const base::MotionState dummy_motion_state = base::MotionState::MOVING; // ???
    const base::ObjectType dummy_type = base::ObjectType::VEHICLE; //???
    const Eigen::Matrix4d radar2world_pose = radar_trans.matrix();

    // Loop over all raw objects and translate to base::Objects
    for(auto &raw_obj : raw_radar_detections_) {
      
      base::ObjectPtr radar_object = std::make_shared<base::Object>();

      radar_object->id = raw_obj.id;
      //radar_object->track_id = ??? // TODO!
      Eigen::Vector4d local_loc(raw_obj.x,
                              raw_obj.y, 0, 1);
      Eigen::Vector4d world_loc =
        static_cast<Eigen::Matrix<double, 4, 1, 0, 4, 1>>(radar2world_pose *
                                                          local_loc);
      radar_object->center = world_loc.block<3, 1>(0, 0);
      radar_object->anchor_point = radar_object->center;
      Eigen::Vector3d local_vel(raw_obj.v, 0.0, 0.0);
      Eigen::Matrix3d radar2world_rotate = radar2world_pose.block<3, 3>(0, 0);
      Eigen::Vector3d world_vel =
          static_cast<Eigen::Matrix<double, 3, 1, 0, 3, 1> >(
              radar2world_rotate * local_vel);
      Eigen::Vector3d vehicle_vel(loct_ptr->pose().linear_velocity().x(),
                                  loct_ptr->pose().linear_velocity().y(),
                                  loct_ptr->pose().linear_velocity().z());
      radar_object->velocity = (vehicle_vel + world_vel).cast<float>();
      radar_object->center_uncertainty.setIdentity() * dummy_uncertainty;
      radar_object->velocity_uncertainty.setIdentity() * dummy_uncertainty;
      double ego_theta = loct_ptr->pose().heading(); // for the production radar sensors == obstacle orientation!
      Eigen::Vector3f direction(static_cast<float>(cos(ego_theta)),
                               static_cast<float>(sin(ego_theta)), 0.0f);
      direction = radar2world_rotate.cast<float>() * direction;
      radar_object->direction = direction;
      radar_object->theta = std::atan2(direction(1), direction(0)); //== heading?
      radar_object->theta_variance = dummy_uncertainty;
      radar_object->confidence = dummy_confidence;
      radar_object->motion_state = dummy_motion_state;
      radar_object->type = dummy_type;
      radar_object->size(0) = dummy_object_length;
      radar_object->size(1) = dummy_object_width;
      radar_object->size(2) = dummy_object_height; 
      apollo::perception::radar::MockRadarPolygon(radar_object);
      float local_range = static_cast<float>(local_loc.head(2).norm());
      float local_angle =
          static_cast<float>(std::atan2(local_loc(1), local_loc(0)));
      radar_object->radar_supplement.range = local_range;
      radar_object->radar_supplement.angle = local_angle;

      out_message->frame_->objects.push_back(radar_object);

      ADEBUG  << "Postprocessed Radar Obj: " 
              << " id = " << radar_object->id 
              << " x = " << radar_object->center.x() 
              << " y = " << radar_object->center.y() 
              << " v_x = " << radar_object->velocity.x() 
              << " v_y = " << radar_object->velocity.y();
    }

  return true;
  }

//! From the provided timestamp, get the matching localization and tf; use latest loca if no timestamp provided
bool UmrrRadarDetectionComponent::GetLocalizationAndTransform(
  const bool& chassis_detail_has_time, 
  const double& chassis_detail_time,
  std::shared_ptr<SensorFrameMessage>& out_message, 
  std::shared_ptr<LocalizationEstimate const>& loct_ptr, 
  Eigen::Affine3d& radar_trans) {
    // Get Localization and Time
    double transformation_timestamp;
    if(chassis_detail_has_time) { //if the timestamp is provided by the chassis detail msg
      if(!localization_subscriber_.LookupNearest(chassis_detail_time, &loct_ptr)) { 
        out_message->error_code_ = apollo::common::ErrorCode::PERCEPTION_ERROR_UNKNOWN;
        AERROR << "Could not get loclization at time " << chassis_detail_time;
        return false;
      }
      transformation_timestamp = chassis_detail_time;
    } else { //if chassis detail does not provide a timestamp
      if (!localization_subscriber_.LookupLatest(&loct_ptr)) { 
        out_message->error_code_ = apollo::common::ErrorCode::PERCEPTION_ERROR_UNKNOWN;
        AERROR << "Could not get latest loclization!";
        return false;
      } 
      transformation_timestamp = loct_ptr->header().timestamp_sec();
    }

    // Get Transform
    // For fortuna built -in radars we consider radar detecions pre-calibrated in
    // ego frame (mid point of rear-vehicle axis)
    radar_trans.setIdentity();
    if (!radar2world_trans_.GetSensor2worldTrans(transformation_timestamp, &radar_trans)) { //! TODO using the loca timestamp here is a hack!! we have to get the timestamp into chassis detail!
      out_message->error_code_ = apollo::common::ErrorCode::PERCEPTION_ERROR_TF;
      AERROR << "Failed to get pose at time: " << transformation_timestamp;
      return false;
    }

    return true;
  }

//! Gather all radar data from Chassis Detail Msg and store it in raw_radar_detections_
bool UmrrRadarDetectionComponent::GetRawRadarData(
  const std::shared_ptr<ChassisDetail>& in_message,
  const double& chassis_detail_time) {
      
  raw_radar_detections_.clear();

  if (in_message->has_fortuna()) {
    if(in_message->mutable_fortuna()->has_front_object_1()) {
      ProcessFrontObject(in_message->mutable_fortuna()->mutable_front_object_1());
    }
    if(in_message->mutable_fortuna()->has_front_object_2()) {
      ProcessFrontObject(in_message->mutable_fortuna()->mutable_front_object_2());
    }
    if(in_message->mutable_fortuna()->has_front_object_3()) {
      ProcessFrontObject(in_message->mutable_fortuna()->mutable_front_object_3());
    }
    if(in_message->mutable_fortuna()->has_front_object_4()) {
      ProcessFrontObject(in_message->mutable_fortuna()->mutable_front_object_4());
    }
    if(in_message->mutable_fortuna()->has_rear_object_1()) {
      ProcessRearObject(in_message->mutable_fortuna()->mutable_rear_object_1());
    }
    if(in_message->mutable_fortuna()->has_rear_object_2()) {
      ProcessRearObject(in_message->mutable_fortuna()->mutable_rear_object_2());
    }
    if(in_message->mutable_fortuna()->has_rear_object_3()) {
      ProcessRearObject(in_message->mutable_fortuna()->mutable_rear_object_3());
    }
    if(in_message->mutable_fortuna()->has_rear_object_4()) {
      ProcessRearObject(in_message->mutable_fortuna()->mutable_rear_object_4());
    }
    if(in_message->mutable_fortuna()->has_rear_object_5()) {
      ProcessRearObject(in_message->mutable_fortuna()->mutable_rear_object_5());
    }
    if(in_message->mutable_fortuna()->has_rear_object_6()) {
      ProcessRearObject(in_message->mutable_fortuna()->mutable_rear_object_6());
    }
  }
  
  // Debug outputs
  if(!raw_radar_detections_.empty()) {
    for(auto &entry : raw_radar_detections_) {
      ADEBUG << "Raw Radar Object at time = "  << chassis_detail_time << " id = " << entry.id << " x = " << entry.x << " y = " << entry.y << " v = " << entry.v;
    }
  }

  return true;
}

//! Read the raw can data for a front object message and parse it into the raw_radar_detections_ vector
template<class UmrrRadarCanFrame>
  void UmrrRadarDetectionComponent::ProcessFrontObject(const UmrrRadarCanFrame obj) {
    if(obj->id() != 0) { //object is valid
        RawRadarDetections rrd;
        rrd.id = obj->id();
        rrd.x = obj->rel_pos_x();
        rrd.y = obj->rel_pos_y();
        rrd.v = obj->rel_velocity_x();
        raw_radar_detections_.push_back(rrd);
      }
  }

  //! Read the raw can data for a rear object message and parse it into the raw_radar_detections_ vector
  template<class UmrrRadarCanFrame>
  void UmrrRadarDetectionComponent::ProcessRearObject(const UmrrRadarCanFrame obj) {
    if(obj->rear_id() != 0) { //object is valid
        RawRadarDetections rrd;
        rrd.id = obj->rear_id();
        rrd.x = obj->rear_pos_x();
        rrd.y = obj->rear_pos_y();
        rrd.v = obj->rear_rel_velocity_x();
        raw_radar_detections_.push_back(rrd);
      }
  }


}  // namespace onboard
}  // namespace perception
}  // namespace apollo
