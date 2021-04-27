/******************************************************************************
 * Copyright 2021 fortiss GmbH
 * Authors: Tobias Kessler, Klemens Esterle
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *****************************************************************************/

#include "modules/planning/planner/miqp/trajectory_smoother_nlopt.h"

#include <nlopt.h>

#include <iostream>

#include "cyber/common/log.h"
#include "modules/common/time/time.h"

// Create function pointers for nlopt outside the namespace
double nlopt_objective_wrapper(unsigned n, const double* x, double* grad,
                               void* data) {
  apollo::planning::TrajectorySmootherNLOpt* obj =
      static_cast<apollo::planning::TrajectorySmootherNLOpt*>(data);
  return obj->ObjectiveFunction(n, x, grad);
}

void nlopt_inequality_constraint_wrapper(unsigned m, double* result, unsigned n,
                                         const double* x, double* grad,
                                         void* data) {
  apollo::planning::TrajectorySmootherNLOpt* obj =
      static_cast<apollo::planning::TrajectorySmootherNLOpt*>(data);
  obj->InequalityConstraintFunction(m, result, n, x, grad);
}

void nlopt_equality_constraint_wrapper(unsigned m, double* result, unsigned n,
                                       const double* x, double* grad,
                                       void* data) {
  apollo::planning::TrajectorySmootherNLOpt* obj =
      static_cast<apollo::planning::TrajectorySmootherNLOpt*>(data);
  obj->EqualityConstraintFunction(m, result, n, x, grad);
}

namespace apollo {
namespace planning {

using namespace Eigen;
using apollo::common::time::Clock;

TrajectorySmootherNLOpt::TrajectorySmootherNLOpt() {
  // TODO Set costs

  x0_.resize(STATES::STATES_SIZE);

  num_ineq_constr_ = 0;
  num_eq_constr_ = 0;
  numevals_ = 0;
}

void TrajectorySmootherNLOpt::InitializeProblem(
    const int subsampling, const DiscretizedTrajectory& input_trajectory,
    const common::TrajectoryPoint& planning_init_point) {
  ready_to_optimize_ = false;
  input_traj_size_ = input_trajectory.size();
  subsampling_ = subsampling;
  if (input_traj_size_ < 1) {
    AERROR << "Empty input trajectory!";
    return;
  }
  if (input_traj_size_ == 1) {
    AINFO << "Input trajectory has only one point, no need for smoothing!";
    return;
  }

  // set problem size
  int nr_intermediate_pts = (input_traj_size_ - 1) * subsampling_;
  nr_integration_steps_ = input_traj_size_ + nr_intermediate_pts;
  problem_size_ = nr_integration_steps_ * INPUTS::INPUTS_SIZE;
  // x_ is resized in IntegrateModel()

  stepsize_ = input_trajectory.at(1).relative_time() -
              input_trajectory.at(0).relative_time();
  stepsize_ = stepsize_ / (subsampling_ + 1);
  initial_time_ = input_trajectory.at(0).relative_time();

  // set x0 using the reference traj
  x0_[STATES::X] = input_trajectory.front().path_point().x();
  x0_[STATES::Y] = input_trajectory.front().path_point().y();
  x0_[STATES::THETA] = input_trajectory.front().path_point().theta();
  x0_[STATES::V] = input_trajectory.front().v();
  x0_[STATES::A] = input_trajectory.front().a();
  x0_[STATES::KAPPA] = input_trajectory.front().path_point().kappa();

  // set reference from input
  X_ref_.resize(input_traj_size_ * STATES::STATES_SIZE);
  int offset = 0;
  for (auto& pt : input_trajectory) {
    X_ref_[offset + STATES::X] = pt.path_point().x();
    X_ref_[offset + STATES::Y] = pt.path_point().y();
    X_ref_[offset + STATES::THETA] = pt.path_point().theta();
    X_ref_[offset + STATES::V] = pt.v();
    X_ref_[offset + STATES::A] = pt.a();
    X_ref_[offset + STATES::KAPPA] = pt.path_point().kappa();
    offset += STATES::STATES_SIZE;
  }

  u_.resize(problem_size_);
  last_u_.resize(problem_size_);
  // set u0: start values for the optimizer
  // choose the intermediate points with the same jerk and xi as the previous
  // input point
  int idx_u = 0;
  for (int idx_input = 0; idx_input < input_traj_size_; ++idx_input) {
    // not at the last idx --> do subsampling
    if (idx_input < input_traj_size_ - 1) {
      for (int idx_subsample = 0; idx_subsample <= subsampling_;
           ++idx_subsample) {
        u_[idx_u + INPUTS::J] =
            BoundedJerk(input_trajectory.at(idx_input).da());
        u_[idx_u + INPUTS::XI] = BoundedCurvatureChange(
            input_trajectory.at(idx_input).path_point().dkappa());
        idx_u += INPUTS::INPUTS_SIZE;
      }
    } else {  // dont subsample last point
      u_[idx_u + INPUTS::J] = input_trajectory.at(idx_input).da();
      u_[idx_u + INPUTS::XI] =
          input_trajectory.at(idx_input).path_point().dkappa();
    }
  }

  // set lower and upper bound vector
  lower_bound_.resize(problem_size_);
  upper_bound_.resize(problem_size_);
  for (size_t idx = 0; idx < problem_size_; idx += 2) {
    lower_bound_.at(idx + INPUTS::J) = params_.lower_bound_jerk;
    lower_bound_.at(idx + INPUTS::XI) = params_.lower_bound_curvature_change;
    upper_bound_.at(idx + INPUTS::J) = params_.upper_bound_jerk;
    upper_bound_.at(idx + INPUTS::XI) = params_.upper_bound_curvature_change;
  }

  status_ = 0;
  ready_to_optimize_ = true;
}

int TrajectorySmootherNLOpt::Optimize() {
  if (!ready_to_optimize_) {
    AERROR << "Optimization Problem was not initialized!";
    return -100;
  }

  // Initialize the optimization problem
  nlopt::opt opt(solver_params_.algorithm, problem_size_);

  // Options
  opt.set_xtol_rel(solver_params_.x_tol_rel);
  opt.set_xtol_abs(solver_params_.x_tol_abs);
  opt.set_maxeval(solver_params_.max_num_evals);

  // Upper and lower bound on u
  if (!lower_bound_.empty()) {
    opt.set_lower_bounds(lower_bound_);
  }
  if (!upper_bound_.empty()) {
    opt.set_upper_bounds(upper_bound_);
  }

  // Objective Function
  opt.set_min_objective(nlopt_objective_wrapper, this);

  // Constraints
  if (num_ineq_constr_ > 0) {
    ineq_constraint_tol_.clear();
    ineq_constraint_tol_.resize(num_ineq_constr_,
                                solver_params_.ineq_const_tol);
    opt.add_inequality_mconstraint(nlopt_inequality_constraint_wrapper, this,
                                   ineq_constraint_tol_);
  }

  if (num_eq_constr_ > 0) {
    eq_constraint_tol_.clear();
    eq_constraint_tol_.resize(num_eq_constr_, solver_params_.eq_const_tol);
    opt.add_equality_mconstraint(nlopt_equality_constraint_wrapper, this,
                                 eq_constraint_tol_);
  }

  AINFO << "Starting smoothing optimization";
  double current_time = Clock::NowInSeconds();

  // Optimization
  try {
    status_ = static_cast<int>(opt.optimize(u_, j_opt_));
  } catch (nlopt::roundoff_limited ex) {
    AWARN << "Roundoff limited exception:" << ex.what();
  } catch (std::bad_alloc ex) {
    AWARN << "Out of memory exception:" << ex.what();
  } catch (std::invalid_argument ex) {
    AWARN << "Invalid argument exception:" << ex.what();
  } catch (std::runtime_error ex) {
    AWARN << "Generic failure exception:" << ex.what();
  } catch (std::exception ex) {
    AERROR << "Unhandled Exception while optimization: " << ex.what();
    status_ = -11;
    return status_;
  }

  AINFO << "Smoothing optimization finished with final cost of " << j_opt_
        << " in " << (Clock::NowInSeconds() - current_time) << "s and with "
        << numevals_ << " iterations";

  switch (status_) {
    case nlopt::SUCCESS:
      AINFO << "Generic success return value.";
      break;
    case nlopt::STOPVAL_REACHED:
      AINFO << "Optimization stopped because stopval was reached.";
      break;
    case nlopt::FTOL_REACHED:
      AINFO << "Optimization stopped because ftol_rel or ftol_abs was reached.";
      break;
    case nlopt::XTOL_REACHED:
      AINFO << "Optimization stopped because xtol_rel or xtol_abs was reached.";
      break;
    case nlopt::MAXEVAL_REACHED:
      AINFO << "Optimization stopped because maxeval was reached.";
      break;
    case nlopt::INVALID_ARGS:
      AWARN << "Invalid arguments (e.g. lower bounds are bigger than upper "
               "bounds, "
               "an unknown algorithm was specified, etcetera).";
      break;
    case nlopt::OUT_OF_MEMORY:
      AWARN << "Ran out of memory.";
      break;
    case nlopt::ROUNDOFF_LIMITED:
      AWARN << "Halted because roundoff errors limited progress. (In this "
               "case, the "
               "optimization still typically returns a useful result.)";
      status_ = 10;
      break;
    default:
      ///@see http://ab-initio.mit.edu/wiki/index.php/NLopt_Reference
      AINFO << "Generic return value: " << status_;
  }

  //  TODO do we need this???
  //   if (!checkConstraints()) {
  //     AERROR << "Constraints are not satisfied within tolerance.";
  //     status_ = -10;  // extra status value...
  //   }

  if (status_ > 0) {
    AINFO << "Smoothing optimization successful."
          << " NlOpt Status: " << status_;
  } else {
    AERROR << "Smoothing optimization failed."
           << " NlOpt Status: " << status_;
  }
  return status_;
}

DiscretizedTrajectory TrajectorySmootherNLOpt::GetOptimizedTrajectory() {
  DiscretizedTrajectory traj;
  const int size_state_vector = X_.rows();
  double s = 0.0f;
  double lastx = X_[STATES::X];
  double lasty = X_[STATES::Y];
  for (int idx = 0; idx < size_state_vector / STATES::STATES_SIZE; ++idx) {
    common::TrajectoryPoint tp;
    const double x = X_[idx * STATES::STATES_SIZE + STATES::X];
    const double y = X_[idx * STATES::STATES_SIZE + STATES::Y];
    tp.mutable_path_point()->set_x(x);
    tp.mutable_path_point()->set_y(y);
    s += sqrt(pow(x - lastx, 2) + pow(y - lasty, 2));
    tp.mutable_path_point()->set_s(s);
    tp.mutable_path_point()->set_theta(
        X_[idx * STATES::STATES_SIZE + STATES::THETA]);
    tp.mutable_path_point()->set_kappa(
        X_[idx * STATES::STATES_SIZE + STATES::KAPPA]);
    tp.set_v(X_[idx * STATES::STATES_SIZE + STATES::V]);
    tp.set_a(X_[idx * STATES::STATES_SIZE + STATES::A]);
    // TODO do we have to use idx-1 for the inputs?
    tp.set_da(u_[idx * INPUTS::INPUTS_SIZE + INPUTS::J]);
    tp.mutable_path_point()->set_dkappa(
        u_[idx * INPUTS::INPUTS_SIZE + INPUTS::XI]);
    tp.set_relative_time(initial_time_ + idx * stepsize_);
    traj.AppendTrajectoryPoint(tp);
    lastx = x;
    lasty = y;
  }
  return traj;
}

double TrajectorySmootherNLOpt::ObjectiveFunction(unsigned n, const double* x,
                                                  double* grad) {
  // TODO optimize computation time: only compute values if the respective cost
  // terms are nonzero!

  double J = 0;
  Map<const VectorXd> u_eigen(x, n);
  Map<VectorXd> grad_eigen(grad, n);
  if (grad != NULL) {
    grad_eigen.fill(0);
  }

  CalculateCommonDataIfNecessary(u_eigen);

  // Costs on reference deviation and states
  // differences vector: for x,y,theta,v compute state-ref for each
  // non-subsampled point absolute vector: for a,kappa copy the value from X_
  const int size_state_vector = X_.rows();
  VectorXd difference;
  difference.setZero(size_state_vector);
  VectorXd absolute;
  absolute.setZero(size_state_vector);
  VectorXd difference_costs;
  difference_costs.setZero(size_state_vector);
  VectorXd absolute_costs;
  absolute_costs.setZero(size_state_vector);
  Vector6d costs_state;
  costs_state << params_.cost_offset_x, params_.cost_offset_y,
      params_.cost_offset_theta, params_.cost_offset_v,
      params_.cost_acceleration, params_.cost_curvature;
  for (int idx = 0; idx < size_state_vector / STATES::STATES_SIZE; ++idx) {
    if (idx % (subsampling_ + 1) == 0) {  // not a subsampled step
      size_t idx_vec = idx * STATES::STATES_SIZE;
      size_t idx_vec_sub = idx / (subsampling_ + 1) * STATES::STATES_SIZE;
      for (int element = 0; element < 4; ++element) {  // only for x,y,theta,v
        difference[idx_vec + element] =
            X_[idx_vec + element] - X_ref_[idx_vec_sub + element];
        difference_costs[idx_vec + element] = costs_state[element];
      }
      absolute[idx_vec + STATES::A] = X_[idx_vec + STATES::A];
      absolute_costs[idx_vec + STATES::A] = costs_state[STATES::A];
      absolute[idx_vec + STATES::KAPPA] = X_[idx_vec + STATES::KAPPA];
      absolute_costs[idx_vec + STATES::KAPPA] = costs_state[STATES::KAPPA];
    }
  }

  // Costs on inputs
  VectorXd absolute_inputs;
  absolute_inputs.setZero(n);
  VectorXd costs_inputs;
  costs_inputs.setZero(n);
  for (int idx = 0; idx < static_cast<int>(n) / INPUTS::INPUTS_SIZE; ++idx) {
    if (idx % (subsampling_ + 1) == 0) {  // not a subsampled step
      absolute_inputs[idx * INPUTS::INPUTS_SIZE + INPUTS::J] =
          u_eigen[idx * INPUTS::INPUTS_SIZE + INPUTS::J];
      absolute_inputs[idx * INPUTS::INPUTS_SIZE + INPUTS::XI] =
          u_eigen[idx * INPUTS::INPUTS_SIZE + INPUTS::XI];
      costs_inputs[idx * INPUTS::INPUTS_SIZE + INPUTS::J] =
          params_.cost_acceleration_change;
      costs_inputs[idx * INPUTS::INPUTS_SIZE + INPUTS::XI] =
          params_.cost_curvature_change;
    }
  }

  // Compute cost term
  J += difference.transpose() * difference.cwiseProduct(difference_costs);
  J += absolute.transpose() * absolute.cwiseProduct(absolute_costs);
  J += absolute_inputs.transpose() * absolute_inputs.cwiseProduct(costs_inputs);

  // Gradients: Derivate of J
  if (grad != NULL) {
    grad_eigen +=
        2 * dXdU_.transpose() * difference.cwiseProduct(difference_costs);
    grad_eigen += 2 * dXdU_.transpose() * absolute.cwiseProduct(absolute_costs);
    grad_eigen += 2 * absolute_inputs.cwiseProduct(costs_inputs);
  }

  numevals_ += 1;
  return J;
}

void TrajectorySmootherNLOpt::InequalityConstraintFunction(
    unsigned m, double* result, unsigned n, const double* x, double* grad) {}

void TrajectorySmootherNLOpt::EqualityConstraintFunction(
    unsigned m, double* result, unsigned n, const double* x, double* grad) {}

void TrajectorySmootherNLOpt::IntegrateModel(const Vector6d& x0,
                                             const Eigen::VectorXd& u,
                                             const size_t num_integration_steps,
                                             const double h, Eigen::VectorXd& X,
                                             Eigen::MatrixXd& dXdU) {
  constexpr size_t dimX = STATES::STATES_SIZE;
  constexpr size_t dimU = INPUTS::INPUTS_SIZE;
  const size_t N = num_integration_steps;

  X.resize(dimX * N);
  X.block<dimX, 1>(0, 0) = x0;

  dXdU.resize(dimX * N, dimU * N);
  dXdU.fill(0.0f);

  currB_.resize(dimX, dimU);

  size_t row_idx, row_idx_before, u_idx;

  for (size_t i = 1; i < N; ++i) {
    row_idx = i * dimX;
    row_idx_before = (i - 1) * dimX;

    Eigen::Vector2d u_curr = u.block<dimU, 1>((i - 1) * dimU, 0);

    const Vector6d& x_before = X.block<dimX, 1>(row_idx_before, 0);
    model_f(x_before, u_curr, h, currx_);
    model_dfdx(x_before, u_curr, h, currA_);
    model_dfdu(x_before, u_curr, h, currB_);

    X.block<dimX, 1>(row_idx, 0) = currx_;
    dXdU.block<dimX, dimU>(row_idx, (i - 1) * dimU) = currB_;

    dXdU.block<dimX, dimU>(row_idx, dimU * (N - 1)) =
        currA_ * dXdU.block<dimX, dimU>(row_idx_before, dimU * (N - 1));

    for (size_t idx_n = 1; idx_n < i; ++idx_n) {
      u_idx = (idx_n - 1) * dimU;
      dXdU.block<dimX, dimU>(row_idx, u_idx) =
          currA_ * dXdU.block<dimX, dimU>(row_idx_before, u_idx);
    }
  }
}

void TrajectorySmootherNLOpt::model_f(const Vector6d& x,
                                      const Eigen::Vector2d& u, const double h,
                                      Vector6d& x_out) {
  const double sinth = sin(x(STATES::THETA));
  const double costh = cos(x(STATES::THETA));
  const double c1 = x(STATES::V) + h * x(STATES::A);
  const double c2 = x(STATES::THETA) + h * x(STATES::V) * x(STATES::KAPPA);
  const double c3 = x(STATES::KAPPA) + h * u(INPUTS::XI);
  const double c4 = x(STATES::A) + h * u(INPUTS::J);

  const double x1 =
      x(STATES::X) + 0.5 * h * x(STATES::V) * costh + 0.5 * h * c1 * cos(c2);
  const double y1 =
      x(STATES::Y) + 0.5 * h * x(STATES::V) * sinth + 0.5 * h * c1 * sin(c2);
  const double theta1 = x(STATES::THETA) +
                        0.5 * h * x(STATES::V) * x(STATES::KAPPA) +
                        0.5 * h * c1 * c3;
  const double v1 = x(STATES::V) + 0.5 * h * x(STATES::A) + 0.5 * h * c4;
  const double a1 = c4;
  const double kappa1 = c3;
  x_out << x1, y1, theta1, v1, a1, kappa1;
}

void TrajectorySmootherNLOpt::model_dfdx(const Vector6d& x,
                                         const Eigen::Vector2d& u,
                                         const double h, Matrix6d& dfdx_out) {
  const double sinth = sin(x(STATES::THETA));
  const double costh = cos(x(STATES::THETA));
  const double c1 = x(STATES::V) + h * x(STATES::A);
  const double c2 = x(STATES::THETA) + h * x(STATES::V) * x(STATES::KAPPA);

  const double dx1_dth0 = -0.5 * h * x(STATES::V) * sinth - 0.5 * c1 * sin(c2);
  const double dy1_dth0 =
      0.5 * h * x(STATES::V) * costh + 0.5 * h * c1 * cos(c2);

  const double dx1_dv0 = 0.5 * h * costh + 0.5 * h * cos(c2) -
                         0.5 * pow(h, 2) * x(STATES::KAPPA) * c1 * sin(c2);
  const double dy1_dv0 = 0.5 * h * sinth + 0.5 * h * sin(c2) +
                         0.5 * pow(h, 2) * x(STATES::KAPPA) * c1 * cos(c2);
  const double dth1_dv0 =
      h * x(STATES::KAPPA) + 0.5 * pow(h, 2) * u(INPUTS::XI);

  const double dx1_da0 = 0.5 * pow(h, 2) * cos(c2);
  const double dy1_da0 = 0.5 * pow(h, 2) * sin(c2);
  const double dth1_da0 =
      0.5 * pow(h, 2) * (x(STATES::KAPPA) + h * u(INPUTS::XI));

  const double dx1_dkappa0 = -0.5 * pow(h, 2) * x(STATES::V) * c1 * sin(c2);
  const double dy1_dkappa0 = 0.5 * pow(h, 2) * x(STATES::V) * c1 * cos(c2);
  const double dth1_dkappa0 = h * x(STATES::V) + 0.5 * pow(h, 2) * x(STATES::A);

  dfdx_out << 1, 0, dx1_dth0, dx1_dv0, dx1_da0, dx1_dkappa0, 0, 1, dy1_dth0,
      dy1_dv0, dy1_da0, dy1_dkappa0, 0, 0, 1, dth1_dv0, dth1_da0, dth1_dkappa0,
      0, 0, 0, 1, h, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1;
}

void TrajectorySmootherNLOpt::model_dfdu(const Vector6d& x,
                                         const Eigen::Vector2d& u,
                                         const double h,
                                         Eigen::MatrixXd& dfdxi_out) {
  dfdxi_out << 0, 0, 0, 0.5 * pow(h, 2), h, 0, 0, 0,
      0.5 * pow(h, 2) * x(STATES::V) + 0.5 * pow(h, 3) * x(STATES::A), 0, 0, h;
}

void TrajectorySmootherNLOpt::CalculateCommonDataIfNecessary(
    const Eigen::VectorXd& u) {
  if (u != last_u_ || last_u_.size() != u.size()) {
    last_u_ = u;
    IntegrateModel(x0_, u, nr_integration_steps_, stepsize_, X_, dXdU_);
  }
}

void TrajectorySmootherNLOpt::DebugDumpX() const {
  std::cout << "X = [ \n";
  for (size_t i = 0; i < X_.rows(); i++) {
    std::cout << X_(i);
    if (i != X_.rows() - 1) std::cout << ", \n";
  }
  std::cout << "]\n\n";
}

void TrajectorySmootherNLOpt::DebugDumpXref() const {
  std::cout << "X_ref = [ \n";
  for (size_t i = 0; i < X_ref_.rows(); i++) {
    std::cout << X_ref_(i);
    if (i != X_ref_.rows() - 1) std::cout << ", \n";
  }
  std::cout << "]\n\n";
}

void TrajectorySmootherNLOpt::DebugDumpU() const {
  std::cout << "u = [ \n";
  for (size_t i = 0; i < last_u_.rows(); ++i) {
    std::cout << last_u_(i);
    if (i != last_u_.rows() - 1) std::cout << ", \n";
  }
  std::cout << "]\n\n";
}

double TrajectorySmootherNLOpt::BoundedJerk(const double val) const {
  return std::max(std::min(val, params_.upper_bound_jerk),
                  params_.lower_bound_jerk);
}

double TrajectorySmootherNLOpt::BoundedCurvatureChange(const double val) const {
  return std::max(std::min(val, params_.upper_bound_curvature_change),
                  params_.lower_bound_curvature_change);
}

}  // namespace planning
}  // namespace apollo