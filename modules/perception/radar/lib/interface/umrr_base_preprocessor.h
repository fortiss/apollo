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
// SAMPLE CODE:
//
// class DefaultPreprocessor : public UmrrBasePreprocessor {
//  public:
//   DefaultPreprocessor() : UmrrBasePreprocessor() {}
//   virtual ~DefaultPreprocessor() {}
//
//   virtual bool Init() override {
//     // Do something.
//     return true;
//   }
//
//   virtual bool Preprocess(
//           const drivers::ContiRadar& raw_obstacles,
//           const PreprocessorOptions& options,
//           drivers::ContiRadar* corrected_obstacles) override {
//      // Do something.
//      return true;
//    }
//
//    virtual std::string Name() const override {
//        return "DefaultPreprocessor";
//    }
//
// };
//
// // Register plugin.
// PERCEPTION_REGISTER_PREPROCESSOR(DefaultPreprocessor);
////////////////////////////////////////////////////////
// USING CODE:
//
// UmrrBasePreprocessor* preprocessor =
//    UmrrBasePreprocessorRegisterer::GetInstanceByName("DefaultPreprocessor");
// using preprocessor to do somethings.
// ////////////////////////////////////////////////////

#pragma once

#include <string>

#include "Eigen/Core"

#include "cyber/common/log.h"
#include "cyber/common/macros.h"

#include "modules/drivers/proto/umrr_radar_objects.pb.h"
#include "modules/perception/base/frame.h"
#include "modules/perception/lib/config_manager/config_manager.h"
#include "modules/perception/lib/registerer/registerer.h"
#include "modules/perception/radar/common/types.h"

namespace apollo {
namespace perception {
namespace radar {

struct PreprocessorOptions {
  // reserved
};

class UmrrBasePreprocessor {
 public:
  UmrrBasePreprocessor() = default;
  virtual ~UmrrBasePreprocessor() = default;

  virtual bool Init() = 0;

  // @brief: correct radar raw obstacles.
  // @param [in]: raw obstacles from radar driver.
  // @param [in]: options.
  // @param [out]: corrected radar obstacles
  virtual bool Preprocess(const drivers::UmrrRadar& raw_obstacles,
                          const PreprocessorOptions& options,
                          drivers::UmrrRadar* corrected_obstacles) = 0;

  virtual std::string Name() const = 0;

 private:
  DISALLOW_COPY_AND_ASSIGN(UmrrBasePreprocessor);
};

PERCEPTION_REGISTER_REGISTERER(UmrrBasePreprocessor);
#define PERCEPTION_REGISTER_PREPROCESSOR(name) \
  PERCEPTION_REGISTER_CLASS(UmrrBasePreprocessor, name)

}  // namespace radar
}  // namespace perception
}  // namespace apollo
