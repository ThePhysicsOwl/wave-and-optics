from __future__ import annotations

import csv
from pathlib import Path
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMenu, QMessageBox, QStyle, QToolBar, QToolButton

from physics import HorizontalSlider, SimplePendulum, VerticalLoadedSpring
from render.canvas import PhysicsCanvas
from .docks import EnergyDock, KinematicsDock, OscillationMetricsDock, PhaseSpaceDock, SidebarDock


SYSTEM_CLASSES = {
    "Vertical Loaded Spring": VerticalLoadedSpring,
    "Horizontal Spring": HorizontalSlider,
    "Simple Pendulum": SimplePendulum,
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Harmonic Oscillator Lab")
        self.resize(1400, 900)
        self.setDockNestingEnabled(True)
        self.setAnimated(False)
        self._history = []
        self._install_app_icon()
        self._install_dark_theme()

        self.system = VerticalLoadedSpring()
        self.system.set_initial_conditions(0.0, 0.0)
        self.is_playing = False
        self._last_tick = time.perf_counter()

        self._init_toolbar()
        self._init_central_canvas()
        self._init_docks()
        self._init_panel_visibility_controls()
        self._apply_default_panel_visibility()
        self._init_timer()

        self._apply_parameters(self.sidebar_dock.current_parameters())
        self._configure_plots_for_system()
        self._reset_analysis()
        self._draw_current_state(record=True)
        self.statusBar().showMessage("Ready")

    def _init_toolbar(self) -> None:
        self.toolbar = QToolBar("Playback")
        self.toolbar.setObjectName("PlaybackToolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        style = self.style()
        self.play_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "Play", self)
        self.pause_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaPause), "Pause", self)
        self.reset_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "Reset", self)
        self.grid_action = QAction("Grid", self)
        self.grid_action.setCheckable(True)
        self.grid_action.setChecked(True)
        self.upload_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Upload Data", self)
        self.export_action = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Export Data", self)

        self.play_action.triggered.connect(lambda _checked=False: self.set_playing(True))
        self.pause_action.triggered.connect(lambda _checked=False: self.set_playing(False))
        self.reset_action.triggered.connect(lambda _checked=False: self.reset_sim())
        self.grid_action.toggled.connect(self._toggle_grid)
        self.upload_action.triggered.connect(lambda _checked=False: self._upload_placeholder())
        self.export_action.triggered.connect(lambda _checked=False: self._export_csv())

        self.toolbar.addAction(self.play_action)
        self.toolbar.addAction(self.pause_action)
        self.toolbar.addAction(self.reset_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.grid_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.upload_action)
        self.toolbar.addAction(self.export_action)
        self._sync_playback_actions()

    def _init_central_canvas(self) -> None:
        self.canvas = PhysicsCanvas(self)
        self.setCentralWidget(self.canvas)
        self.canvas.drag_started.connect(self._handle_drag_started)
        self.canvas.drag_changed.connect(self._handle_drag_changed)
        self.canvas.drag_released.connect(self._handle_drag_released)

    def _init_docks(self) -> None:
        self.sidebar_dock = SidebarDock("Simulation Parameters", self)
        self.sidebar_dock.parameters_changed.connect(self._apply_parameters)
        self.sidebar_dock.system_changed.connect(self._switch_system)
        self.sidebar_dock.initial_conditions_changed.connect(self._apply_custom_initial_conditions)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock)

        self.kinematics_dock = KinematicsDock("Kinematics", self)
        self.phase_dock = PhaseSpaceDock("Phase Space", self)
        self.energy_dock = EnergyDock("Energy", self)
        self.metrics_dock = OscillationMetricsDock("Oscillation Metrics", self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.kinematics_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.phase_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.energy_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.metrics_dock)
        self.splitDockWidget(self.phase_dock, self.energy_dock, Qt.Orientation.Vertical)
        self.splitDockWidget(self.energy_dock, self.metrics_dock, Qt.Orientation.Vertical)

    def _init_panel_visibility_controls(self) -> None:
        self.panels_menu = QMenu("Panels", self)
        self._managed_docks = [
            self.sidebar_dock,
            self.kinematics_dock,
            self.phase_dock,
            self.energy_dock,
            self.metrics_dock,
        ]
        for dock in self._managed_docks:
            self.panels_menu.addAction(dock.toggleViewAction())
        self.panels_menu.addSeparator()

        show_all_action = QAction("Show All Panels", self)
        show_all_action.triggered.connect(self._show_all_panels)
        self.panels_menu.addAction(show_all_action)

        panel_button = QToolButton(self)
        panel_button.setText("Panels")
        panel_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        panel_button.setMenu(self.panels_menu)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(panel_button)

    def _apply_default_panel_visibility(self) -> None:
        self.sidebar_dock.show()
        self.kinematics_dock.show()
        self.phase_dock.hide()
        self.energy_dock.hide()
        self.metrics_dock.hide()

    def _init_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.update_sim)
        self._frame_counter = 0

    def set_playing(self, playing: bool) -> None:
        self.is_playing = bool(playing)
        if self.is_playing:
            self._last_tick = time.perf_counter()
            self.timer.start(16)
            self.statusBar().showMessage("Running")
        else:
            self.timer.stop()
            self.statusBar().showMessage("Paused")
        self._sync_playback_actions()

    def reset_sim(self) -> None:
        self.set_playing(False)
        x0 = 0.45 if self.system.visual_mode == "pendulum" else 1.0
        self.system.set_initial_conditions(x0, 0.0)
        self.canvas.set_system(self.system.visual_mode, self.system.visual_parameters())
        self._reset_analysis()
        self._draw_current_state(record=True)
        self.statusBar().showMessage("Reset")

    def update_sim(self) -> None:
        now = time.perf_counter()
        dt = min(max(now - self._last_tick, 1.0 / 240.0), 1.0 / 20.0)
        self._last_tick = now
        try:
            state = self.system.step(dt)
            self._frame_counter += 1
            render_graphs = (self._frame_counter % 2 == 0)
            self._record_state(state, render_graphs)
            self.canvas.update_visuals(state.x)
        except Exception as e:
            print(f"Physics error: {e}")
            self.set_playing(False)

    def _switch_system(self, system_name: str) -> None:
        self.set_playing(False)
        self.system = SYSTEM_CLASSES[system_name]()
        self._apply_parameters(self.sidebar_dock.current_parameters(), preserve_state=False)
        self._configure_plots_for_system()
        self.reset_sim()

    def _apply_parameters(self, params: dict[str, float], preserve_state: bool = True) -> None:
        self.system.set_parameters(
            mass=params["mass"],
            k=params["k"],
            damping=params["damping"],
            driving_force=params["driving_force"],
            preserve_state=preserve_state,
        )
        self._update_derived_quantities()
        self.canvas.set_system(self.system.visual_mode, self.system.visual_parameters())
        self.canvas.update_visuals(self.system.x)
        if hasattr(self, "energy_dock"):
            self._draw_current_state(record=False)

    def _configure_plots_for_system(self) -> None:
        self.kinematics_dock.set_coordinate_label(self.system.coordinate_name, self.system.coordinate_units)
        self.phase_dock.set_coordinate_label(self.system.coordinate_name, self.system.coordinate_units)
        self.metrics_dock.set_coordinate_label(self.system.coordinate_name, self.system.coordinate_units)

    def _update_derived_quantities(self) -> None:
        quantities = self.system.derived_quantities()
        self.sidebar_dock.update_derived_labels(
            quantities["omega0"],
            quantities["zeta"],
            quantities["frequency"],
        )

    def _reset_analysis(self) -> None:
        self._history.clear()
        self.kinematics_dock.reset_data()
        self.phase_dock.reset_data()
        self.energy_dock.reset_data()
        self.metrics_dock.reset_data()

    def _draw_current_state(self, record: bool = False) -> None:
        state = self.system.current_state()
        self.energy_dock.update_bars(state.kinetic, state.potential, state.total)
        self.canvas.update_visuals(state.x)
        if record:
            self._record_state(state, render=True)

    def _record_state(self, state, render: bool = True) -> None:
        self.kinematics_dock.update_graphs(state.t, state.x, state.v, state.acceleration, state.force, render)
        self.phase_dock.update_graphs(state.x, state.v, render)
        self.energy_dock.update_graphs(state.t, state.kinetic, state.potential, state.total, render)
        period, frequency, angular_frequency, amplitude = self._metrics_for_state(state)
        self.metrics_dock.update_graphs(state.t, period, frequency, angular_frequency, amplitude, render)
        self._history.append(self._history_row_for_state(state, period, frequency, angular_frequency, amplitude))

    def _handle_drag_started(self) -> None:
        self.set_playing(False)
        self._reset_analysis()

    def _handle_drag_changed(self, coordinate: float, velocity: float) -> None:
        self.system.set_initial_conditions(coordinate, velocity)
        self.sidebar_dock.set_initial_condition_values(coordinate, velocity)
        state = self.system.current_state()
        self.energy_dock.update_bars(state.kinetic, state.potential, state.total)

    def _handle_drag_released(self, coordinate: float, velocity: float) -> None:
        self.system.set_initial_conditions(coordinate, velocity)
        self.sidebar_dock.set_initial_condition_values(coordinate, velocity)
        self._reset_analysis()
        self._draw_current_state(record=True)
        self.set_playing(True)

    def _apply_custom_initial_conditions(self, coordinate: float, velocity: float) -> None:
        self.set_playing(False)
        self.system.set_initial_conditions(coordinate, velocity)
        self._reset_analysis()
        self._draw_current_state(record=True)
        self.statusBar().showMessage("Initial state set")

    def _toggle_grid(self, visible: bool) -> None:
        self.canvas.set_grid_visible(visible)

    def _upload_placeholder(self) -> None:
        QMessageBox.information(self, "Import Data", "Feature unavailable")

    def _export_csv(self) -> None:
        if not self._history:
            QMessageBox.information(self, "Export Data", "No simulation data is available to export.")
            return

        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Simulation Data",
            "harmonic_oscillator_export.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return

        export_path = Path(path)
        if export_path.suffix.lower() != ".csv":
            export_path = export_path.with_suffix(".csv")

        fieldnames = list(self._history[0].keys())
        try:
            with export_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self._history)
        except OSError as exc:
            QMessageBox.critical(self, "Export Data", f"Could not export CSV data:\n{exc}")
            return

        self.statusBar().showMessage(f"Exported {len(self._history)} rows to {export_path}")

    def _sync_playback_actions(self) -> None:
        self.play_action.setEnabled(not self.is_playing)
        self.pause_action.setEnabled(self.is_playing)

    def _metrics_for_state(self, state) -> tuple[float, float, float, float]:
        metrics = self.system.oscillation_metrics(state)
        return (
            metrics["period"],
            metrics["frequency"],
            metrics["angular_frequency"],
            metrics["amplitude"],
        )

    def _history_row_for_state(
        self,
        state,
        period: float,
        frequency: float,
        angular_frequency: float,
        amplitude: float,
    ) -> dict[str, float | str]:
        params = self.sidebar_dock.current_parameters()
        return {
            "system": self.system.name,
            "time_s": state.t,
            "coordinate_name": self.system.coordinate_name,
            "coordinate_units": self.system.coordinate_units,
            "coordinate": state.x,
            "velocity": state.v,
            "acceleration": state.acceleration,
            "force_N": state.force,
            "kinetic_energy_J": state.kinetic,
            "potential_energy_J": state.potential,
            "total_energy_J": state.total,
            "period_s": period,
            "frequency_Hz": frequency,
            "angular_frequency_rad_s": angular_frequency,
            "amplitude": amplitude,
            "mass_kg": params["mass"],
            "stiffness_or_length": params["k"],
            "damping": params["damping"],
            "driving_force_or_torque": params["driving_force"],
        }

    def _show_all_panels(self) -> None:
        for dock in self._managed_docks:
            dock.show()
            dock.raise_()

    def _install_dark_theme(self) -> None:
        try:
            import qdarkstyle

            self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt6"))
            return
        except Exception:
            pass

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #020617;
                color: #dbeafe;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 12px;
            }
            QToolBar {
                background: #0f172a;
                border-bottom: 1px solid #1e293b;
                spacing: 8px;
                padding: 6px;
            }
            QToolButton, QPushButton {
                background: #111827;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QToolButton:hover, QPushButton:hover {
                border-color: #22d3ee;
            }
            QDockWidget {
                titlebar-close-icon: none;
                titlebar-normal-icon: none;
            }
            QDockWidget::title {
                background: #0f172a;
                border: 1px solid #1e293b;
                padding: 8px;
                text-align: left;
            }
            QGroupBox {
                border: 1px solid #1e293b;
                border-radius: 8px;
                margin-top: 12px;
                padding: 12px 8px 8px 8px;
                background: #07111f;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #93c5fd;
            }
            QComboBox, QDoubleSpinBox, QMessageBox {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 5px;
            }
            QSlider::groove:horizontal {
                background: #1e293b;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #22d3ee;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QLabel#MissingCanvasBackend {
                color: #bfdbfe;
                font-size: 16px;
                padding: 24px;
            }
            """
        )

    def _install_app_icon(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        icon_path = project_root / "icon.ico"
        if not icon_path.exists():
            icon_path = project_root / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def closeEvent(self, event) -> None:
        self.canvas.close()
        super().closeEvent(event)
