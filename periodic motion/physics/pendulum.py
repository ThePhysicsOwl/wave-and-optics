from __future__ import annotations

from math import acos, cos, isfinite, pi, sin, sqrt

try:
    from scipy.integrate import solve_ivp
    from scipy.special import ellipk
except Exception:  # pragma: no cover - exercised only on lean installs.
    solve_ivp = None
    ellipk = None

from .base import OscillatorState, PhysicsSystem


class SimplePendulum(PhysicsSystem):
    """Large-angle pendulum with high-precision numerical integration."""

    name = "Simple Pendulum"
    visual_mode = "pendulum"
    coordinate_name = "theta"
    coordinate_units = "rad"

    def __init__(
        self,
        mass: float = 1.0,
        k: float = 2.5,
        damping: float = 0.05,
        driving_force: float = 0.0,
    ) -> None:
        super().__init__(mass=mass, k=k, damping=damping, driving_force=driving_force)
        self.x = 0.0
        self._x0 = self.x

    @property
    def length(self) -> float:
        return max(self.k, 0.1)

    def set_initial_conditions(self, x0: float, v0: float = 0.0) -> None:
        limit = pi * 0.92
        super().set_initial_conditions(max(min(float(x0), limit), -limit), float(v0))

    def get_state(self, t: float) -> OscillatorState:
        t = max(float(t), 0.0)
        if t == 0.0:
            x, v = self._x0, self._v0
        else:
            x, v = self._integrate_from_origin(t)
        return self.energies_to_state(t, x, v, self._energy_for(x, v), self.dynamics_for(x, v))

    def step(self, dt: float) -> OscillatorState:
        dt = max(float(dt), 0.0)
        if dt == 0.0:
            return self.current_state()

        self.x, self.v = self._integrate(self.x, self.v, dt)
        self.t += dt
        return self.current_state()

    def get_energy(self) -> tuple[float, float, float]:
        return self._energy_for(self.x, self.v)

    def derived_quantities(self) -> dict[str, float]:
        metrics = self._nonlinear_metrics_for(self.x, self.v)
        omega0 = metrics["angular_frequency"]
        damping_per_inertia = self.b / max(self.mass * self.length * self.length, 1.0e-12)
        zeta = damping_per_inertia / (2.0 * max(omega0, 1.0e-12))
        return {
            "omega0": omega0,
            "zeta": zeta,
            "frequency": metrics["frequency"],
        }

    def visual_parameters(self) -> dict[str, float]:
        return {"length": self.length}

    def dynamics_for(self, x: float, v: float) -> tuple[float, float]:
        angular_acceleration = self._rhs(0.0, (x, v))[1]
        tangential_force = self.mass * self.length * angular_acceleration
        return angular_acceleration, tangential_force

    def oscillation_metrics(self, state: OscillatorState) -> dict[str, float]:
        return self._nonlinear_metrics_for(state.x, state.v)

    def _rhs(self, _t: float, y: tuple[float, float] | list[float]) -> tuple[float, float]:
        theta, omega = y
        inertia = max(self.mass * self.length * self.length, 1.0e-12)
        damping = self.b / inertia
        drive = self.f0 / inertia
        acceleration = -(9.81 / self.length) * sin(theta) - damping * omega + drive
        return omega, acceleration

    def _integrate_from_origin(self, duration: float) -> tuple[float, float]:
        return self._integrate(self._x0, self._v0, duration)

    def _integrate(self, theta: float, omega: float, duration: float) -> tuple[float, float]:
        if solve_ivp is not None:
            try:
                solution = solve_ivp(
                    self._rhs,
                    (0.0, duration),
                    (theta, omega),
                    method="DOP853",
                    rtol=1.0e-9,
                    atol=1.0e-11,
                )
                if solution.success:
                    return float(solution.y[0, -1]), float(solution.y[1, -1])
            except Exception:
                pass
        return self._rk4(theta, omega, duration)

    def _rk4(self, theta: float, omega: float, duration: float) -> tuple[float, float]:
        steps = max(1, int(duration / 0.004))
        h = duration / steps
        y0 = theta
        y1 = omega
        for _ in range(steps):
            k1 = self._rhs(0.0, (y0, y1))
            k2 = self._rhs(0.0, (y0 + 0.5 * h * k1[0], y1 + 0.5 * h * k1[1]))
            k3 = self._rhs(0.0, (y0 + 0.5 * h * k2[0], y1 + 0.5 * h * k2[1]))
            k4 = self._rhs(0.0, (y0 + h * k3[0], y1 + h * k3[1]))
            y0 += (h / 6.0) * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
            y1 += (h / 6.0) * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
        return y0, y1

    def _energy_for(self, theta: float, omega: float) -> tuple[float, float, float]:
        kinetic = 0.5 * self.mass * (self.length * omega) ** 2
        potential = self.mass * 9.81 * self.length * (1.0 - cos(theta))
        return kinetic, potential, kinetic + potential

    def _nonlinear_metrics_for(self, theta: float, omega: float) -> dict[str, float]:
        amplitude = self._energy_equivalent_amplitude(theta, omega)
        period = self._large_angle_period(amplitude)
        frequency = 1.0 / period if period > 1.0e-12 else 0.0
        return {
            "period": period,
            "frequency": frequency,
            "angular_frequency": 2.0 * pi * frequency,
            "amplitude": amplitude,
        }

    def _energy_equivalent_amplitude(self, theta: float, omega: float) -> float:
        _, _, total = self._energy_for(theta, omega)
        gravitational_scale = max(self.mass * 9.81 * self.length, 1.0e-12)
        cos_amplitude = 1.0 - total / gravitational_scale
        cos_amplitude = max(-1.0 + 1.0e-9, min(1.0, cos_amplitude))
        return acos(cos_amplitude)

    def _large_angle_period(self, amplitude: float) -> float:
        amplitude = max(0.0, min(abs(amplitude), pi - 1.0e-6))
        parameter = sin(0.5 * amplitude) ** 2
        if ellipk is not None:
            integral = float(ellipk(parameter))
        else:
            integral = self._complete_elliptic_integral_first_kind(parameter)
        if not isfinite(integral):
            return 0.0
        return 4.0 * sqrt(self.length / 9.81) * integral

    @staticmethod
    def _complete_elliptic_integral_first_kind(parameter: float) -> float:
        a = 1.0
        b = sqrt(max(1.0 - parameter, 1.0e-12))
        for _ in range(18):
            next_a = 0.5 * (a + b)
            next_b = sqrt(a * b)
            a, b = next_a, next_b
        return pi / (2.0 * a)
