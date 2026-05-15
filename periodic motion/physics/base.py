from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class OscillatorState:
    """A sampled state used by the UI, render loop, and future exporters."""

    t: float
    x: float
    v: float
    kinetic: float
    potential: float
    total: float
    acceleration: float = 0.0
    force: float = 0.0


class PhysicsSystem:
    """
    Base interface shared by analytical and numerical oscillator models.

    The generalized coordinate is named ``x`` for the UI. For pendulums it is
    the angular displacement in radians; for springs it is linear displacement
    in metres relative to equilibrium.
    """

    name = "Physics System"
    visual_mode = "vertical_spring"
    coordinate_name = "x"
    coordinate_units = "m"

    def __init__(
        self,
        mass: float = 1.0,
        k: float = 10.0,
        damping: float = 0.5,
        driving_force: float = 0.0,
    ) -> None:
        self.mass = mass
        self.k = k
        self.b = damping
        self.f0 = driving_force

        self.t = 0.0
        self.x = 1.0
        self.v = 0.0
        self._x0 = self.x
        self._v0 = self.v

    def set_parameters(
        self,
        *,
        mass: float | None = None,
        k: float | None = None,
        damping: float | None = None,
        driving_force: float | None = None,
        preserve_state: bool = True,
    ) -> None:
        """Update physical parameters, optionally continuing from this state."""

        current_x = self.x
        current_v = self.v

        if mass is not None:
            self.mass = max(float(mass), 1.0e-6)
        if k is not None:
            self.k = max(float(k), 1.0e-6)
        if damping is not None:
            self.b = max(float(damping), 0.0)
        if driving_force is not None:
            self.f0 = float(driving_force)

        if preserve_state:
            self.set_initial_conditions(current_x, current_v)

    def set_initial_conditions(self, x0: float, v0: float = 0.0) -> None:
        """Reset elapsed time and use the supplied state as the new origin."""

        self.t = 0.0
        self.x = float(x0)
        self.v = float(v0)
        self._x0 = self.x
        self._v0 = self.v

    def step(self, dt: float) -> OscillatorState:
        """Advance the system by ``dt`` seconds."""

        raise NotImplementedError

    def get_state(self, t: float) -> OscillatorState:
        """Return the state at elapsed time ``t`` from the current origin."""

        raise NotImplementedError

    def get_energy(self) -> tuple[float, float, float]:
        """Return kinetic, potential, and total energy at the current state."""

        raise NotImplementedError

    def dynamics_for(self, x: float, v: float) -> tuple[float, float]:
        """Return generalized acceleration and force for a coordinate state."""

        return 0.0, 0.0

    def current_state(self) -> OscillatorState:
        """Return a complete state object for the current in-memory state."""

        return self.energies_to_state(self.t, self.x, self.v, self.get_energy(), self.dynamics_for(self.x, self.v))

    def rest_initial_conditions(self) -> tuple[float, float]:
        """Return the zero-energy reset state for this system."""

        return 0.0, 0.0

    def derived_quantities(self) -> Dict[str, float]:
        """Return standard linearized quantities for the sidebar readouts."""

        omega0 = sqrt(max(self.k / self.mass, 0.0))
        zeta = self.b / (2.0 * sqrt(max(self.mass * self.k, 1.0e-12)))
        return {
            "omega0": omega0,
            "zeta": zeta,
            "frequency": omega0 / (2.0 * pi),
        }

    def oscillation_metrics(self, state: OscillatorState) -> Dict[str, float]:
        """Return period/frequency metrics for plotting."""

        quantities = self.derived_quantities()
        angular_frequency = quantities["omega0"]
        frequency = quantities["frequency"]
        period = 1.0 / frequency if frequency > 1.0e-12 else 0.0
        return {
            "period": period,
            "frequency": frequency,
            "angular_frequency": angular_frequency,
            "amplitude": abs(state.x),
        }

    def visual_parameters(self) -> Dict[str, float]:
        """Optional parameters consumed by the 3D canvas."""

        return {}

    def sample(self, duration: float, dt: float) -> List[OscillatorState]:
        """Convenience helper for future export and testing workflows."""

        if duration <= 0.0 or dt <= 0.0:
            return []
        count = int(duration / dt) + 1
        return [self.get_state(i * dt) for i in range(count)]

    @staticmethod
    def energies_to_state(
        t: float,
        x: float,
        v: float,
        energies: Iterable[float],
        dynamics: Iterable[float] = (0.0, 0.0),
    ) -> OscillatorState:
        kinetic, potential, total = energies
        acceleration, force = dynamics
        return OscillatorState(
            t=t,
            x=x,
            v=v,
            kinetic=kinetic,
            potential=potential,
            total=total,
            acceleration=acceleration,
            force=force,
        )
