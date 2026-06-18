library(tidyverse)

sim_data <- as.tibble(
  read.csv("data/harmonic_oscillator_export.csv")
)

sim_data <- sim_data |>
  select(-c(system, coordinate_name, coordinate_units)) |>
  rename(
    t = time_s,
    theta = coordinate,
    v = velocity,
    accel = acceleration,
    tau = force_N,
    K = kinetic_energy_J,
    U = potential_energy_J,
    E = total_energy_J,
    T = period_s,
    freq = frequency_Hz,
    omega = angular_frequency_rad_s,
    amplitude = amplitude,
    m = mass_kg,
    l = stiffness_or_length,
    b = damping,
    tau_d = driving_force_or_torque,
    omega_d = driving_frequency_rad_s
  )

# specify list of constants
const_list <- c("m", "l", "b", "tau_d", "omega_d")
const_values <- numeric(length(const_list))

# constant-pulling function
pull_const <- function(col_name) {
  sim_data |>
    pull(col_name) |>
    unique()
}

for (i in seq_along(const_list)) {
  const_values[i] <- pull_const(col_name = const_list[i])
}

# Remove constant columns from dataset
sim_data <- sim_data |>
  select(-any_of(const_list))





# Extract each analysis sub tables
extract_cols <- function(x = "t", y) {
  sim_data |>
    select(c(x, y))
}

for (i in colnames(sim_data)[-1]) {
  file_name <- paste0("data/t_vs_", i, ".csv")
  write.csv(
    extract_cols(y = i),
    row.names = FALSE,
    file = file_name
  )
}

# Additional sub tables
write.csv(
  extract_cols(x = "theta", y = "v"),
  row.names = FALSE,
  file = "data/phase_space.csv"
)