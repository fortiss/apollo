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
#pragma once

#include <string>

#include "cyber/common/macros.h"
#include "modules/drivers/proto/umrr_radar_objects.pb.h"
#include "modules/perception/radar/lib/interface/umrr_base_preprocessor.h"

namespace apollo {
namespace perception {
namespace radar {

class UmrrArsPreprocessor : public UmrrBasePreprocessor {
 public:
  UmrrArsPreprocessor() : UmrrBasePreprocessor(), delay_time_(0.0) {}
  virtual ~UmrrArsPreprocessor() {}

  bool Init() override;

  bool Preprocess(const drivers::UmrrRadar& raw_obstacles,
                  const PreprocessorOptions& options,
                  drivers::UmrrRadar* corrected_obstacles) override;

  std::string Name() const override;

  inline double GetDelayTime() { return delay_time_; }

 private:
  void SkipObjects(const drivers::UmrrRadar& raw_obstacles,
                   drivers::UmrrRadar* corrected_obstacles);
  void ExpandIds(drivers::UmrrRadar* corrected_obstacles);
  void CorrectTime(drivers::UmrrRadar* corrected_obstacles);
  int GetNextId();

  float delay_time_ = 0.0f;
  static int current_idx_;
  static int local2global_[ORIGIN_CONTI_MAX_ID_NUM];

  friend class UmrrArsPreprocessorTest;

  DISALLOW_COPY_AND_ASSIGN(UmrrArsPreprocessor);
};

}  // namespace radar
}  // namespace perception
}  // namespace apollo
