/******************************************************************************
 * Copyright 2018 The Apollo Authors. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the License);
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an AS IS BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *****************************************************************************/
#include "modules/perception/radar/lib/preprocessor/umrr_ars_preprocessor/umrr_ars_preprocessor.h"
#include "modules/perception/lib/utils/perf.h"

namespace apollo {
namespace perception {
namespace radar {

int UmrrArsPreprocessor::current_idx_ = 0;
int UmrrArsPreprocessor::local2global_[ORIGIN_CONTI_MAX_ID_NUM] = {0};

bool UmrrArsPreprocessor::Init() {
  std::string model_name = "UmrrArsPreprocessor";
  const lib::ModelConfig* model_config = nullptr;
  CHECK(lib::ConfigManager::Instance()->GetModelConfig(model_name,
                                                       &model_config));
  CHECK(model_config->get_value("delay_time", &delay_time_));
  return true;
}

bool UmrrArsPreprocessor::Preprocess(
    const drivers::UmrrRadar& raw_obstacles,
    const PreprocessorOptions& options,
    drivers::UmrrRadar* corrected_obstacles) {
  PERCEPTION_PERF_FUNCTION();
  SkipObjects(raw_obstacles, corrected_obstacles);
  
  // EW We need this function to store global object ids between different radars -> for smartmicro radar we have 4 of them
  ExpandIds(corrected_obstacles);
  
  CorrectTime(corrected_obstacles);
  return true;
}

std::string UmrrArsPreprocessor::Name() const {
  return "UmrrArsPreprocessor";
}

// EW - This function skips objects which are not within the cycle_duration time interval
// In fact for umrr radar there is information about cycle_duration. I looks like it is not the case for conti radar.
// In general I am not sure if this is needed, because all objects which are currently provided, should come from within the current cycle duration
// However I am not entirely sure of that.
void UmrrArsPreprocessor::SkipObjects(
    const drivers::UmrrRadar& raw_obstacles,
    drivers::UmrrRadar* corrected_obstacles) {
  corrected_obstacles->mutable_header()->CopyFrom(raw_obstacles.header());
  double timestamp = raw_obstacles.header().timestamp_sec() - 1e-6;
  for (const auto& umrrobs : raw_obstacles.umrrobs()) {
    double object_timestamp = umrrobs.header().timestamp_sec();

    //EW UMRR_INTERVAL value is taken from the specification where it's called Cycle_Duration
    if (object_timestamp > timestamp &&
        object_timestamp < timestamp + raw_obstacles.cycle_duration()) {
      drivers::UmrrRadarObs* obs = corrected_obstacles->add_umrrobs();
      *obs = umrrobs;
    }
  }
  if (raw_obstacles.umrrobs_size() > corrected_obstacles->umrrobs_size()) {
    AINFO << "skip objects: " << raw_obstacles.umrrobs_size() << "-> "
          << corrected_obstacles->umrrobs_size();
  }
}

void UmrrArsPreprocessor::ExpandIds(drivers::UmrrRadar* corrected_obstacles) {
  for (int iobj = 0; iobj < corrected_obstacles->umrrobs_size(); ++iobj) {
    const auto& umrrobs = corrected_obstacles->umrrobs(iobj);
    int id = umrrobs.obstacle_id();
    // EW if (CONTI_NEW == umrrobs.meas_state()) {
    //if (CONTI_NEW == 1) {
    //  local2global_[id] = GetNextId();
    // } else {
      if (local2global_[id] == 0) {
        local2global_[id] = GetNextId();
      }
    //}
    corrected_obstacles->mutable_umrrobs(iobj)->set_obstacle_id(
        local2global_[id]);
  }
}

void UmrrArsPreprocessor::CorrectTime(
    drivers::UmrrRadar* corrected_obstacles) {
  double correct_timestamp =
      corrected_obstacles->header().timestamp_sec() - delay_time_;
  corrected_obstacles->mutable_header()->set_timestamp_sec(correct_timestamp);
}

int UmrrArsPreprocessor::GetNextId() {
  ++current_idx_;
  if (MAX_RADAR_IDX == current_idx_) {
    current_idx_ = 1;
  }
  return current_idx_;
}

PERCEPTION_REGISTER_PREPROCESSOR(UmrrArsPreprocessor);

}  // namespace radar
}  // namespace perception
}  // namespace apollo
