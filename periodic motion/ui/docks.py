from __future__ import annotations

import ast
from collections import deque
import math
import operator

import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QValidator
from PyQt6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


pg.setConfigOptions(antialias=True, foreground="#cbd5e1")

DOCK_FEATURES = (
    QDockWidget.DockWidgetFeature.DockWidgetMovable
    | QDockWidget.DockWidgetFeature.DockWidgetFloatable
    | QDockWidget.DockWidgetFeature.DockWidgetClosable
)

_EXPRESSION_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}

_EXPRESSION_FUNCTIONS = {
    "abs": abs,
    "acos": math.acos,
    "asin": math.asin,
    "atan": math.atan,
    "cos": math.cos,
    "degrees": math.degrees,
    "exp": math.exp,
    "log": math.log,
    "radians": math.radians,
    "sin": math.sin,
    "sqrt": math.sqrt,
    "tan": math.tan,
}

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class ExpressionSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that accepts safe math expressions such as ``pi/4``."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setKeyboardTracking(False)
        self.setToolTip("Accepts numbers or expressions such as pi/4, 2*pi, or sqrt(2).")

    def validate(self, text: str, pos: int):
        cleaned = self._clean_text(text)
        if cleaned in {"", "+", "-", ".", "+.", "-."}:
            return QValidator.State.Intermediate, text, pos
        try:
            value = self._evaluate_expression(cleaned)
        except (ArithmeticError, SyntaxError, TypeError, ValueError, OverflowError, ZeroDivisionError):
            return QValidator.State.Intermediate, text, pos
        if not math.isfinite(value):
            return QValidator.State.Invalid, text, pos
        return QValidator.State.Acceptable, text, pos

    def valueFromText(self, text: str) -> float:
        try:
            value = self._evaluate_expression(self._clean_text(text))
        except (ArithmeticError, SyntaxError, TypeError, ValueError, OverflowError, ZeroDivisionError):
            return self.value()
        return max(self.minimum(), min(self.maximum(), float(value)))

    def textFromValue(self, value: float) -> str:
        rendered = f"{value:.{self.decimals()}f}"
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        return rendered or "0"

    def _clean_text(self, text: str) -> str:
        cleaned = text.strip()
        suffix = self.suffix().strip()
        if suffix and cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
        return cleaned

    @classmethod
    def _evaluate_expression(cls, text: str) -> float:
        if not text:
            raise ValueError("empty expression")
        tree = ast.parse(text, mode="eval")
        return float(cls._evaluate_node(tree.body))

    @classmethod
    def _evaluate_node(cls, node) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id in _EXPRESSION_CONSTANTS:
                return _EXPRESSION_CONSTANTS[node.id]
            raise ValueError(f"unknown constant: {node.id}")
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left = cls._evaluate_node(node.left)
            right = cls._evaluate_node(node.right)
            return _BINARY_OPERATORS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            return _UNARY_OPERATORS[type(node.op)](cls._evaluate_node(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id not in _EXPRESSION_FUNCTIONS or node.keywords:
                raise ValueError("unsupported function")
            args = [cls._evaluate_node(arg) for arg in node.args]
            return float(_EXPRESSION_FUNCTIONS[node.func.id](*args))
        raise ValueError("unsupported expression")


class SidebarDock(QDockWidget):
    parameters_changed = pyqtSignal(dict)
    system_changed = pyqtSignal(str)
    initial_conditions_changed = pyqtSignal(float, float)

    SYSTEMS = ("Vertical Loaded Spring", "Horizontal Spring", "Simple Pendulum")

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(DOCK_FEATURES)
        self._updating = False

        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(14)

        system_group = QGroupBox("System")
        system_layout = QVBoxLayout(system_group)
        self.system_combo = QComboBox()
        self.system_combo.addItems(self.SYSTEMS)
        self.system_combo.currentTextChanged.connect(self._on_system_changed)
        system_layout.addWidget(self.system_combo)
        self.layout.addWidget(system_group)

        parameter_group = QGroupBox("Parameters")
        self.parameter_layout = QFormLayout(parameter_group)
        self.parameter_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.mass_label = QLabel("Mass (m)")
        self.mass_slider, self.mass_spin = self._build_parameter_control("mass")
        self.parameter_layout.addRow(self.mass_label, self._slider_with_spin(self.mass_slider, self.mass_spin))

        self.k_label = QLabel("Spring Constant (k)")
        self.k_slider, self.k_spin = self._build_parameter_control("k")
        self.parameter_layout.addRow(self.k_label, self._slider_with_spin(self.k_slider, self.k_spin))

        self.damping_label = QLabel("Damping (b)")
        self.damping_slider, self.damping_spin = self._build_parameter_control("damping")
        self.parameter_layout.addRow(self.damping_label, self._slider_with_spin(self.damping_slider, self.damping_spin))

        self.force_label = QLabel("Driving Force (F0)")
        self.f0_slider, self.f0_spin = self._build_parameter_control("f0")
        self.parameter_layout.addRow(self.force_label, self._slider_with_spin(self.f0_slider, self.f0_spin))
        self.layout.addWidget(parameter_group)

        initial_group = QGroupBox("Initial Conditions")
        initial_layout = QFormLayout(initial_group)
        self.displacement_label = QLabel("Displacement (x)")
        self.displacement_spin = ExpressionSpinBox()
        self.velocity_label = QLabel("Velocity (v)")
        self.velocity_spin = ExpressionSpinBox()
        self.set_initial_button = QPushButton("Set Initial State")
        self.set_initial_button.clicked.connect(self._emit_initial_conditions)
        initial_layout.addRow(self.displacement_label, self.displacement_spin)
        initial_layout.addRow(self.velocity_label, self.velocity_spin)
        initial_layout.addRow(self.set_initial_button)
        self.layout.addWidget(initial_group)

        derived_group = QGroupBox("Derived Quantities")
        derived_layout = QFormLayout(derived_group)
        self.omega_lbl = QLabel("0.000 rad/s")
        self.zeta_lbl = QLabel("0.000")
        self.freq_lbl = QLabel("0.000 Hz")
        derived_layout.addRow("omega", self.omega_lbl)
        derived_layout.addRow("zeta", self.zeta_lbl)
        derived_layout.addRow("f0", self.freq_lbl)
        self.layout.addWidget(derived_group)
        self.layout.addStretch(1)

        self.setWidget(self.widget)
        self.configure_for_system(self.system_combo.currentText())
        self._emit_parameters_changed()

    def current_parameters(self) -> dict[str, float]:
        for spin in (self.mass_spin, self.k_spin, self.damping_spin, self.f0_spin):
            spin.interpretText()
        return {
            "mass": self.mass_spin.value(),
            "k": self.k_spin.value(),
            "damping": self.damping_spin.value(),
            "driving_force": self.f0_spin.value(),
        }

    def configure_for_system(self, system_name: str) -> None:
        self._updating = True
        self._configure_parameter_control("mass", 1, 100, 0.1, 10.0, 0.1, 2, " kg", 1.0)
        if system_name == "Simple Pendulum":
            self.k_label.setText("Length (L)")
            self.force_label.setText("Driving Torque")
            self._configure_parameter_control("k", 3, 80, 0.3, 8.0, 0.1, 2, " m", 2.5)
            self._configure_parameter_control("damping", 0, 100, 0.0, 1.0, 0.01, 3, "", 0.05)
            self._configure_parameter_control("f0", -100, 100, -10.0, 10.0, 0.1, 2, " N m", 0.0)
            self._configure_initial_controls(
                displacement_label="Angular Displacement (theta)",
                velocity_label="Angular Velocity (omega)",
                displacement_range=(-2.89, 2.89),
                velocity_range=(-12.0, 12.0),
                displacement_suffix=" rad",
                velocity_suffix=" rad/s",
                displacement_step=0.01,
                velocity_step=0.05,
            )
        else:
            self.k_label.setText("Spring Constant (k)")
            self.force_label.setText("Driving Force (F0)")
            self._configure_parameter_control("k", 1, 100, 0.01, 100.0, 0.5, 3, " N/m", 10.0)
            self._configure_parameter_control("damping", 0, 100, 0.0, 10.0, 0.05, 3, " N s/m", 0.5)
            self._configure_parameter_control("f0", -100, 100, -10.0, 10.0, 0.1, 2, " N", 0.0)
            self._configure_initial_controls(
                displacement_label="Displacement (x)",
                velocity_label="Velocity (v)",
                displacement_range=(-2.5, 2.5),
                velocity_range=(-10.0, 10.0),
                displacement_suffix=" m",
                velocity_suffix=" m/s",
                displacement_step=0.01,
                velocity_step=0.05,
            )
        self._updating = False

    def set_initial_condition_values(self, displacement: float, velocity: float) -> None:
        self.displacement_spin.blockSignals(True)
        self.velocity_spin.blockSignals(True)
        self.displacement_spin.setValue(float(displacement))
        self.velocity_spin.setValue(float(velocity))
        self.displacement_spin.blockSignals(False)
        self.velocity_spin.blockSignals(False)

    def update_derived_labels(self, omega: float, zeta: float, freq: float) -> None:
        self.omega_lbl.setText(f"{omega:.3f} rad/s")
        self.zeta_lbl.setText(f"{zeta:.3f}")
        self.freq_lbl.setText(f"{freq:.3f} Hz")

    def _build_parameter_control(self, key: str) -> tuple[QSlider, QDoubleSpinBox]:
        slider = QSlider(Qt.Orientation.Horizontal)
        spin = ExpressionSpinBox()
        spin.setMinimumWidth(112)
        slider.valueChanged.connect(lambda value, key=key: self._on_slider_changed(key, value))
        spin.valueChanged.connect(lambda value, key=key: self._on_spin_changed(key, value))
        return slider, spin

    @staticmethod
    def _slider_with_spin(slider: QSlider, spin: QDoubleSpinBox) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(slider, 1)
        layout.addWidget(spin)
        return widget

    def _configure_parameter_control(
        self,
        key: str,
        slider_min: int,
        slider_max: int,
        spin_min: float,
        spin_max: float,
        spin_step: float,
        spin_decimals: int,
        suffix: str,
        value: float,
    ) -> None:
        slider = self._slider_for_key(key)
        spin = self._spin_for_key(key)
        slider.blockSignals(True)
        spin.blockSignals(True)
        slider.setRange(slider_min, slider_max)
        spin.setRange(spin_min, spin_max)
        spin.setSingleStep(spin_step)
        spin.setDecimals(max(spin_decimals, 6))
        spin.setSuffix(suffix)
        spin.setValue(value)
        slider.setValue(self._value_to_slider(key, value))
        slider.blockSignals(False)
        spin.blockSignals(False)

    def _configure_initial_controls(
        self,
        *,
        displacement_label: str,
        velocity_label: str,
        displacement_range: tuple[float, float],
        velocity_range: tuple[float, float],
        displacement_suffix: str,
        velocity_suffix: str,
        displacement_step: float,
        velocity_step: float,
    ) -> None:
        self.displacement_label.setText(displacement_label)
        self.velocity_label.setText(velocity_label)
        for spin, value_range, suffix, step in (
            (self.displacement_spin, displacement_range, displacement_suffix, displacement_step),
            (self.velocity_spin, velocity_range, velocity_suffix, velocity_step),
        ):
            spin.blockSignals(True)
            spin.setRange(value_range[0], value_range[1])
            spin.setSingleStep(step)
            spin.setDecimals(6)
            spin.setSuffix(suffix)
            spin.setValue(0.0)
            spin.blockSignals(False)

    def _on_system_changed(self, system_name: str) -> None:
        self.configure_for_system(system_name)
        self.system_changed.emit(system_name)
        self.parameters_changed.emit(self.current_parameters())

    def _on_slider_changed(self, key: str, value: int) -> None:
        if self._updating:
            return
        spin = self._spin_for_key(key)
        spin.blockSignals(True)
        spin.setValue(self._slider_to_value(key, value))
        spin.blockSignals(False)
        self._emit_parameters_changed()

    def _on_spin_changed(self, key: str, value: float) -> None:
        if self._updating:
            return
        slider = self._slider_for_key(key)
        slider.blockSignals(True)
        slider.setValue(self._value_to_slider(key, value))
        slider.blockSignals(False)
        self._emit_parameters_changed()

    def _emit_parameters_changed(self, *_args) -> None:
        if not self._updating:
            self.parameters_changed.emit(self.current_parameters())

    def _emit_initial_conditions(self) -> None:
        self.displacement_spin.interpretText()
        self.velocity_spin.interpretText()
        self.initial_conditions_changed.emit(self.displacement_spin.value(), self.velocity_spin.value())

    def _slider_to_value(self, key: str, value: int) -> float:
        if key == "mass":
            return value / 10.0
        if key == "k" and self.system_combo.currentText() == "Simple Pendulum":
            return value / 10.0
        if key == "damping":
            return value / 100.0 if self.system_combo.currentText() == "Simple Pendulum" else value / 10.0
        if key == "f0":
            return value / 10.0
        return float(value)

    def _value_to_slider(self, key: str, value: float) -> int:
        if key == "mass":
            scaled = value * 10.0
        elif key == "k" and self.system_combo.currentText() == "Simple Pendulum":
            scaled = value * 10.0
        elif key == "damping":
            scaled = value * 100.0 if self.system_combo.currentText() == "Simple Pendulum" else value * 10.0
        elif key == "f0":
            scaled = value * 10.0
        else:
            scaled = value
        slider = self._slider_for_key(key)
        return max(slider.minimum(), min(slider.maximum(), int(round(scaled))))

    def _slider_for_key(self, key: str) -> QSlider:
        if key == "mass":
            return self.mass_slider
        if key == "k":
            return self.k_slider
        if key == "damping":
            return self.damping_slider
        return self.f0_slider

    def _spin_for_key(self, key: str) -> QDoubleSpinBox:
        if key == "mass":
            return self.mass_spin
        if key == "k":
            return self.k_spin
        if key == "damping":
            return self.damping_spin
        return self.f0_spin


class KinematicsDock(QDockWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(DOCK_FEATURES)
        self.widget = pg.GraphicsLayoutWidget()
        self.setWidget(self.widget)

        self.position_plot = self.widget.addPlot(row=0, col=0, title="Position vs Time")
        self.velocity_plot = self.widget.addPlot(row=0, col=1, title="Velocity vs Time")
        self.acceleration_plot = self.widget.addPlot(row=1, col=0, title="Acceleration vs Time")
        self.force_plot = self.widget.addPlot(row=1, col=1, title="Force vs Time")
        for plot in (self.position_plot, self.velocity_plot, self.acceleration_plot, self.force_plot):
            _style_plot(plot)
        self.position_curve = self.position_plot.plot(pen=pg.mkPen("#22d3ee", width=2))
        self.velocity_curve = self.velocity_plot.plot(pen=pg.mkPen("#fb923c", width=2))
        self.acceleration_curve = self.acceleration_plot.plot(pen=pg.mkPen("#facc15", width=2))
        self.force_curve = self.force_plot.plot(pen=pg.mkPen("#34d399", width=2))

        self.time_data = deque(maxlen=900)
        self.x_data = deque(maxlen=900)
        self.v_data = deque(maxlen=900)
        self.a_data = deque(maxlen=900)
        self.force_data = deque(maxlen=900)
        self.set_coordinate_label("x", "m")

    def set_coordinate_label(self, name: str, units: str) -> None:
        force_title = "Tangential Force" if name == "theta" else "Force"
        self.position_plot.setTitle(f"{name} vs Time")
        self.velocity_plot.setTitle(f"d{name}/dt vs Time")
        self.acceleration_plot.setTitle(f"d2{name}/dt2 vs Time")
        self.force_plot.setTitle(f"{force_title} vs Time")
        self.position_plot.setLabel("left", name, units=units)
        self.velocity_plot.setLabel("left", f"d{name}/dt", units=f"{units}/s")
        self.acceleration_plot.setLabel("left", f"d2{name}/dt2", units=f"{units}/s^2")
        self.force_plot.setLabel("left", force_title, units="N")
        for plot in (self.position_plot, self.velocity_plot, self.acceleration_plot, self.force_plot):
            plot.setLabel("bottom", "t", units="s")

    def reset_data(self) -> None:
        self.time_data.clear()
        self.x_data.clear()
        self.v_data.clear()
        self.a_data.clear()
        self.force_data.clear()
        self.position_curve.setData([], [])
        self.velocity_curve.setData([], [])
        self.acceleration_curve.setData([], [])
        self.force_curve.setData([], [])
        for plot in (self.position_plot, self.velocity_plot, self.acceleration_plot, self.force_plot):
            _set_dynamic_y_range(plot, [])

    def update_graphs(self, t: float, x: float, v: float, acceleration: float, force: float, render: bool = True) -> None:
        self.time_data.append(t)
        self.x_data.append(x)
        self.v_data.append(v)
        self.a_data.append(acceleration)
        self.force_data.append(force)
        
        if render:
            times = list(self.time_data)
            self.position_curve.setData(times, list(self.x_data))
            self.velocity_curve.setData(times, list(self.v_data))
            self.acceleration_curve.setData(times, list(self.a_data))
            self.force_curve.setData(times, list(self.force_data))
            _set_dynamic_y_range(self.position_plot, self.x_data)
            _set_dynamic_y_range(self.velocity_plot, self.v_data)
            _set_dynamic_y_range(self.acceleration_plot, self.a_data)
            _set_dynamic_y_range(self.force_plot, self.force_data)


class PhaseSpaceDock(QDockWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(DOCK_FEATURES)
        self.widget = pg.GraphicsLayoutWidget()
        self.setWidget(self.widget)

        self.phase_plot = self.widget.addPlot(title="Phase Space")
        _style_plot(self.phase_plot)
        self.phase_curve = self.phase_plot.plot(pen=pg.mkPen("#a78bfa", width=2))
        self.x_data = deque(maxlen=900)
        self.v_data = deque(maxlen=900)
        self.set_coordinate_label("x", "m")

    def set_coordinate_label(self, name: str, units: str) -> None:
        self.phase_plot.setLabel("bottom", name, units=units)
        self.phase_plot.setLabel("left", f"d{name}/dt", units=f"{units}/s")

    def reset_data(self) -> None:
        self.x_data.clear()
        self.v_data.clear()
        self.phase_curve.setData([], [])
        _set_dynamic_y_range(self.phase_plot, [])

    def update_graphs(self, x: float, v: float, render: bool = True) -> None:
        self.x_data.append(x)
        self.v_data.append(v)
        if render:
            self.phase_curve.setData(list(self.x_data), list(self.v_data))
            _set_dynamic_y_range(self.phase_plot, self.v_data)


class EnergyDock(QDockWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(DOCK_FEATURES)
        self.widget = pg.GraphicsLayoutWidget()
        self.setWidget(self.widget)

        self.energy_plot = self.widget.addPlot(row=0, col=0, title="Energy Bars")
        self.energy_history_plot = self.widget.addPlot(row=1, col=0, title="Energy vs Time")
        _style_plot(self.energy_plot)
        _style_plot(self.energy_history_plot)
        self.energy_plot.setLabel("left", "Energy", units="J")
        self.energy_history_plot.setLabel("left", "Energy", units="J")
        self.energy_history_plot.setLabel("bottom", "t", units="s")
        self.energy_plot.getAxis("bottom").setTicks([[(0, "K"), (1, "U"), (2, "Total")]])
        self.kinetic_bar = pg.BarGraphItem(x=[0], height=[0], width=0.55, brush="#22d3ee")
        self.potential_bar = pg.BarGraphItem(x=[1], height=[0], width=0.55, brush="#fb923c")
        self.total_bar = pg.BarGraphItem(x=[2], height=[0], width=0.55, brush="#a78bfa")
        self.energy_plot.addItem(self.kinetic_bar)
        self.energy_plot.addItem(self.potential_bar)
        self.energy_plot.addItem(self.total_bar)
        self.kinetic_curve = self.energy_history_plot.plot(pen=pg.mkPen("#22d3ee", width=2), name="K")
        self.potential_curve = self.energy_history_plot.plot(pen=pg.mkPen("#fb923c", width=2), name="U")
        self.total_curve = self.energy_history_plot.plot(pen=pg.mkPen("#a78bfa", width=2), name="Total")
        self.time_data = deque(maxlen=900)
        self.kinetic_data = deque(maxlen=900)
        self.potential_data = deque(maxlen=900)
        self.total_data = deque(maxlen=900)

    def reset_data(self) -> None:
        self.time_data.clear()
        self.kinetic_data.clear()
        self.potential_data.clear()
        self.total_data.clear()
        self.kinetic_curve.setData([], [])
        self.potential_curve.setData([], [])
        self.total_curve.setData([], [])
        self.update_bars(0.0, 0.0, 0.0)
        _set_dynamic_y_range(self.energy_history_plot, [])

    def update_bars(self, kinetic: float, potential: float, total: float) -> None:
        values = [max(kinetic, 0.0), max(potential, 0.0), max(total, 0.0)]
        self.kinetic_bar.setOpts(height=[values[0]])
        self.potential_bar.setOpts(height=[values[1]])
        self.total_bar.setOpts(height=[values[2]])
        
        target_max = max(1.0, max(values) * 1.18)
        view = self.energy_plot.getViewBox()
        if view is not None:
            current_range = view.state['viewRange'][1]
            if target_max > current_range[1] or target_max < current_range[1] * 0.6:
                self.energy_plot.setYRange(0.0, target_max, padding=0.0)

    def update_graphs(self, t: float, kinetic: float, potential: float, total: float, render: bool = True) -> None:
        if render:
            self.update_bars(kinetic, potential, total)
        self.time_data.append(t)
        self.kinetic_data.append(kinetic)
        self.potential_data.append(potential)
        self.total_data.append(total)
        if render:
            times = list(self.time_data)
            self.kinetic_curve.setData(times, list(self.kinetic_data))
            self.potential_curve.setData(times, list(self.potential_data))
            self.total_curve.setData(times, list(self.total_data))
            _set_dynamic_y_range(self.energy_history_plot, list(self.kinetic_data) + list(self.potential_data) + list(self.total_data))


class OscillationMetricsDock(QDockWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(DOCK_FEATURES)
        self.widget = pg.GraphicsLayoutWidget()
        self.setWidget(self.widget)

        self.period_plot = self.widget.addPlot(row=0, col=0, title="Period vs Time")
        self.frequency_plot = self.widget.addPlot(row=0, col=1, title="Frequency vs Time")
        self.angular_frequency_plot = self.widget.addPlot(row=1, col=0, title="Angular Frequency vs Time")
        self.amplitude_plot = self.widget.addPlot(row=1, col=1, title="Amplitude vs Time")
        for plot in (self.period_plot, self.frequency_plot, self.angular_frequency_plot, self.amplitude_plot):
            _style_plot(plot)

        self.period_curve = self.period_plot.plot(pen=pg.mkPen("#38bdf8", width=2))
        self.frequency_curve = self.frequency_plot.plot(pen=pg.mkPen("#f97316", width=2))
        self.angular_frequency_curve = self.angular_frequency_plot.plot(pen=pg.mkPen("#c084fc", width=2))
        self.amplitude_curve = self.amplitude_plot.plot(pen=pg.mkPen("#34d399", width=2))

        self.time_data = deque(maxlen=900)
        self.period_data = deque(maxlen=900)
        self.frequency_data = deque(maxlen=900)
        self.angular_frequency_data = deque(maxlen=900)
        self.amplitude_data = deque(maxlen=900)
        self.set_coordinate_label("x", "m")

    def set_coordinate_label(self, name: str, units: str) -> None:
        self.period_plot.setLabel("left", "T", units="s")
        self.frequency_plot.setLabel("left", "f", units="Hz")
        self.angular_frequency_plot.setLabel("left", "omega", units="rad/s")
        self.amplitude_plot.setLabel("left", f"|{name}|", units=units)
        for plot in (self.period_plot, self.frequency_plot, self.angular_frequency_plot, self.amplitude_plot):
            plot.setLabel("bottom", "t", units="s")

    def reset_data(self) -> None:
        self.time_data.clear()
        self.period_data.clear()
        self.frequency_data.clear()
        self.angular_frequency_data.clear()
        self.amplitude_data.clear()
        self.period_curve.setData([], [])
        self.frequency_curve.setData([], [])
        self.angular_frequency_curve.setData([], [])
        self.amplitude_curve.setData([], [])
        for plot in (self.period_plot, self.frequency_plot, self.angular_frequency_plot, self.amplitude_plot):
            _set_dynamic_y_range(plot, [])

    def update_graphs(
        self,
        t: float,
        period: float,
        frequency: float,
        angular_frequency: float,
        amplitude: float,
        render: bool = True,
    ) -> None:
        self.time_data.append(t)
        self.period_data.append(period)
        self.frequency_data.append(frequency)
        self.angular_frequency_data.append(angular_frequency)
        self.amplitude_data.append(amplitude)
        if render:
            times = list(self.time_data)
            self.period_curve.setData(times, list(self.period_data))
            self.frequency_curve.setData(times, list(self.frequency_data))
            self.angular_frequency_curve.setData(times, list(self.angular_frequency_data))
            self.amplitude_curve.setData(times, list(self.amplitude_data))
            _set_dynamic_y_range(self.period_plot, self.period_data)
            _set_dynamic_y_range(self.frequency_plot, self.frequency_data)
            _set_dynamic_y_range(self.angular_frequency_plot, self.angular_frequency_data)
            _set_dynamic_y_range(self.amplitude_plot, self.amplitude_data)


def _style_plot(plot) -> None:
    plot.setMenuEnabled(False)
    plot.showGrid(x=True, y=True, alpha=0.18)
    plot.getViewBox().setBackgroundColor("#07111f")
    plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)
    plot.setClipToView(True)
    for axis_name in ("left", "bottom"):
        axis = plot.getAxis(axis_name)
        axis.setPen(pg.mkPen("#334155"))
        axis.setTextPen(pg.mkPen("#cbd5e1"))


def _set_dynamic_y_range(plot, values) -> None:
    if not values:
        plot.setYRange(-1.0, 1.0, padding=0.0)
        return
    try:
        low = min(values)
        high = max(values)
    except Exception:
        plot.setYRange(-1.0, 1.0, padding=0.0)
        return

    span = high - low
    if span < 1.0e-9:
        padding = max(abs(low) * 0.12, 0.1)
    else:
        padding = max(span * 0.12, 0.05)
        
    target_low = low - padding
    target_high = high + padding
    
    view = plot.getViewBox()
    if view is None:
        return
        
    current_range = view.state['viewRange'][1]
    current_span = current_range[1] - current_range[0]
    
    if (target_low < current_range[0] or target_high > current_range[1] or 
        (target_high - target_low) < current_span * 0.6):
        plot.setYRange(target_low, target_high, padding=0.0)
