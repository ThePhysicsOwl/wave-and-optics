from __future__ import annotations

from math import exp, sqrt

from .base import OscillatorState, PhysicsSystem


class DampedLinearOscillator(PhysicsSystem):
    """Exact solution for ``m*x'' + b*x' + k*x = F0``."""

    coordinate_name = "x"
    coordinate_units = "m"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._equilibrium_at_origin = self.equilibrium_offset()

    def equilibrium_offset(self) -> float:
        return self.f0 / self.k if self.k > 1.0e-12 else 0.0

    def set_initial_conditions(self, x0: float, v0: float = 0.0) -> None:
        super().set_initial_conditions(x0, v0)
        self._equilibrium_at_origin = self.equilibrium_offset()

    def get_state(self, t: float) -> OscillatorState:
        t = max(float(t), 0.0)
        x_eq = self._equilibrium_at_origin
        y0 = self._x0 - x_eq
        v0 = self._v0
        omega0 = sqrt(max(self.k / self.mass, 0.0))
        gamma = self.b / (2.0 * self.mass)

        if omega0 < 1.0e-12:
            y = y0 + v0 * t
            v = v0
        elif gamma < 1.0e-12:
            y, v = self._undamped_state(y0, v0, omega0, t)
        elif gamma < omega0:
            y, v = self._underdamped_state(y0, v0, omega0, gamma, t)
        elif abs(gamma - omega0) <= 1.0e-9:
            y, v = self._critically_damped_state(y0, v0, gamma, t)
        else:
            y, v = self._overdamped_state(y0, v0, omega0, gamma, t)

        x = y + x_eq
        return self.energies_to_state(t, x, v, self._energy_for(x, v), self.dynamics_for(x, v))

    def step(self, dt: float) -> OscillatorState:
        self.t = max(self.t + max(float(dt), 0.0), 0.0)
        state = self.get_state(self.t)
        self.x = state.x
        self.v = state.v
        return state

    def get_energy(self) -> tuple[float, float, float]:
        return self._energy_for(self.x, self.v)

    def _energy_for(self, x: float, v: float) -> tuple[float, float, float]:
        kinetic = 0.5 * self.mass * v * v
        potential = 0.5 * self.k * x * x
        return kinetic, potential, kinetic + potential

    def dynamics_for(self, x: float, v: float) -> tuple[float, float]:
        force = self.f0 - self.b * v - self.k * x
        return force / self.mass, force

    @staticmethod
    def _undamped_state(y0: float, v0: float, omega0: float, t: float) -> tuple[float, float]:
        from math import cos, sin

        c = cos(omega0 * t)
        s = sin(omega0 * t)
        y = y0 * c + (v0 / omega0) * s
        v = -y0 * omega0 * s + v0 * c
        return y, v

    @staticmethod
    def _underdamped_state(
        y0: float,
        v0: float,
        omega0: float,
        gamma: float,
        t: float,
    ) -> tuple[float, float]:
        from math import cos, sin

        omega_d = sqrt(max(omega0 * omega0 - gamma * gamma, 0.0))
        c1 = y0
        c2 = (v0 + gamma * y0) / omega_d
        envelope = exp(-gamma * t)
        c = cos(omega_d * t)
        s = sin(omega_d * t)
        y = envelope * (c1 * c + c2 * s)
        v = envelope * ((c2 * omega_d - gamma * c1) * c + (-c1 * omega_d - gamma * c2) * s)
        return y, v

    @staticmethod
    def _critically_damped_state(y0: float, v0: float, gamma: float, t: float) -> tuple[float, float]:
        c1 = y0
        c2 = v0 + gamma * y0
        envelope = exp(-gamma * t)
        y = envelope * (c1 + c2 * t)
        v = envelope * (c2 - gamma * (c1 + c2 * t))
        return y, v

    @staticmethod
    def _overdamped_state(
        y0: float,
        v0: float,
        omega0: float,
        gamma: float,
        t: float,
    ) -> tuple[float, float]:
        root = sqrt(max(gamma * gamma - omega0 * omega0, 0.0))
        if root < 1.0e-12:
            return DampedLinearOscillator._critically_damped_state(y0, v0, gamma, t)
            
        r1 = -gamma + root
        r2 = -gamma - root
        denom = r1 - r2
        c1 = (v0 - r2 * y0) / denom
        c2 = y0 - c1
        
        try:
            e1 = exp(r1 * t)
            e2 = exp(r2 * t)
            y = c1 * e1 + c2 * e2
            v = c1 * r1 * e1 + c2 * r2 * e2
        except OverflowError:
            # If t is large enough to cause overflow, the state has decayed to 0
            y, v = 0.0, 0.0
            
        return y, v


class HorizontalSlider(DampedLinearOscillator):
    name = "Horizontal Spring"
    visual_mode = "horizontal_spring"


class VerticalLoadedSpring(DampedLinearOscillator):
    name = "Vertical Loaded Spring"
    visual_mode = "vertical_spring"


# Backwards-compatible name used by the initial scaffold.
VerticalSpring = VerticalLoadedSpring
