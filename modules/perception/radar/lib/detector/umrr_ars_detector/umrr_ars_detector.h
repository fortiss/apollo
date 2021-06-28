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
#include "modules/perception/radar/common/radar_util.h"
#include "modules/perception/radar/lib/interface/umrr_base_detector.h"

namespace apollo {
namespace perception {
namespace radar {

class UmrrArsDetector : public UmrrBaseDetector {
 public:
  UmrrArsDetector() : UmrrBaseDetector() {}
  virtual ~UmrrArsDetector() {}

  bool Init() override;

  bool Detect(const drivers::UmrrRadar& corrected_obstacles,
              const DetectorOptions& options,
              base::FramePtr detected_frame) override;

  std::string Name() const override;

 private:
  void RawObs2Frame(const drivers::UmrrRadar& corrected_obstacles,
                    const DetectorOptions& options, base::FramePtr radar_frame);

  DISALLOW_COPY_AND_ASSIGN(UmrrArsDetector);
};

}  // namespace radar
}  // namespace perception
}  // namespace apollo
