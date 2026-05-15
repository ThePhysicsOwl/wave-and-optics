from __future__ import annotations

from math import atan2, cos, pi, sin
import os
import time

import numpy as np
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    import pyvista as pv
    from pyvista import _vtk
    from pyvistaqt import QtInteractor
except Exception as exc:  # pragma: no cover - depends on local desktop stack.
    pv = None
    _vtk = None
    QtInteractor = None
    _PYVISTA_IMPORT_ERROR = exc
else:
    _PYVISTA_IMPORT_ERROR = None


class PhysicsCanvas(QWidget):
    """PyVista-backed 3D viewport with direct mass dragging."""

    drag_started = pyqtSignal()
    drag_changed = pyqtSignal(float, float)
    drag_released = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "vertical_spring"
        self._length = 2.5
        self._grid_visible = True
        self._current_coordinate = 1.0
        self._dragging = False
        self._last_drag_coordinate = 1.0
        self._last_drag_time = time.perf_counter()
        self._drag_velocity = 0.0
        self._render_pending = False
        self._visual_update_pending = False
        self._pending_visual_coordinate = None
        self._sphere_radius = 0.22
        self._pivot = np.array([0.0, 0.0, 2.45], dtype=float)
        self._vertical_anchor = np.array([0.0, 0.0, 2.55], dtype=float)
        self._horizontal_anchor = np.array([-3.0, 0.0, 0.0], dtype=float)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.plotter = None
        self.mass_actor = None
        self.spring_mesh = None
        self.string_mesh = None

        if os.environ.get("HARMONIC_OSCILLATOR_DISABLE_3D") == "1":
            self._install_missing_backend_message(RuntimeError("3D canvas disabled by environment"))
            return

        if pv is None or QtInteractor is None:
            self._install_missing_backend_message(_PYVISTA_IMPORT_ERROR)
            return

        try:
            self.plotter = QtInteractor(self, auto_update=False, multi_samples=0)
            self.layout.addWidget(self.plotter)
            self._configure_renderer()
            self._attach_interaction_observers()
            self._rebuild_scene()
        except Exception as exc:
            if self.plotter is not None:
                try:
                    self.plotter.close()
                except Exception:
                    pass
            self.plotter = None
            self._install_missing_backend_message(exc)

    def set_system(self, visual_mode: str, visual_parameters: dict[str, float] | None = None) -> None:
        previous_mode = self._mode
        self._mode = visual_mode
        if visual_parameters and "length" in visual_parameters:
            self._length = max(float(visual_parameters["length"]), 0.25)
        scene_changed = previous_mode != self._mode
        if self.plotter is not None and scene_changed:
            self._rebuild_scene()

    def set_grid_visible(self, visible: bool) -> None:
        self._grid_visible = bool(visible)
        if self.plotter is not None:
            self._rebuild_scene()

    def update_visuals(self, coordinate: float, render: bool = True) -> None:
        self._current_coordinate = float(coordinate)
        if self.plotter is None or self.mass_actor is None:
            return

        mass_position = self._mass_world_position(self._current_coordinate)
        self.mass_actor.SetPosition(*mass_position)

        if self._mode == "pendulum":
            self._update_string(self._pivot, mass_position)
        elif self._mode == "horizontal_spring":
            end = mass_position - np.array([self._sphere_radius, 0.0, 0.0])
            self._update_spring(self._horizontal_anchor, end)
        else:
            end = mass_position + np.array([0.0, 0.0, self._sphere_radius])
            self._update_spring(self._vertical_anchor, end)

        if render:
            self._schedule_render()

    def close(self) -> bool:
        if self.plotter is not None:
            self.plotter.close()
        return super().close()

    def _install_missing_backend_message(self, error: Exception | None = None) -> None:
        message = QLabel(
            "The 3D canvas could not initialize in this Python environment.\n"
            "PyVista/pyvistaqt and a working OpenGL desktop context are required."
        )
        if error is not None:
            message.setToolTip(str(error))
        message.setObjectName("MissingCanvasBackend")
        message.setWordWrap(True)
        self.layout.addWidget(message)

    def _configure_renderer(self) -> None:
        self.plotter.set_background("#030712")
        try:
            self.plotter.enable_parallel_projection()
        except Exception:
            pass

    def _configure_grid(self) -> None:
        try:
            self.plotter.remove_bounds_axes()
        except Exception:
            pass
        if self._grid_visible:
            try:
                self.plotter.show_grid(color="#1e2a3a", font_size=8, location="outer")
            except Exception:
                self.plotter.show_grid()

    def _rebuild_scene(self) -> None:
        self.plotter.clear()
        self._configure_renderer()
        self._configure_grid()

        self.mass_actor = self.plotter.add_mesh(
            pv.Sphere(radius=self._sphere_radius, theta_resolution=48, phi_resolution=24),
            color="#22d3ee",
            smooth_shading=True,
            specular=0.45,
            name="mass",
        )

        if self._mode == "pendulum":
            self._build_pendulum_scene()
        elif self._mode == "horizontal_spring":
            self._build_horizontal_spring_scene()
        else:
            self._build_vertical_spring_scene()

        self.update_visuals(self._current_coordinate, render=False)
        self.plotter.camera_position = [(5.3, -7.4, 4.1), (0.0, 0.0, 0.25), (0.0, 0.0, 1.0)]
        self._schedule_render()

    def _build_vertical_spring_scene(self) -> None:
        self.plotter.add_mesh(pv.Cube(center=self._vertical_anchor, x_length=1.15, y_length=0.16, z_length=0.12), color="#475569")
        self.plotter.add_mesh(pv.Line((-1.25, 0.0, 0.0), (1.25, 0.0, 0.0)), color="#334155", line_width=2)
        self.spring_mesh = self._make_polyline(self._make_spring_points(self._vertical_anchor, np.array([0.0, 0.0, 0.0])))
        self.plotter.add_mesh(self.spring_mesh, color="#38bdf8", line_width=4)
        self.string_mesh = None

    def _build_horizontal_spring_scene(self) -> None:
        self.plotter.add_mesh(pv.Cube(center=self._horizontal_anchor, x_length=0.16, y_length=0.65, z_length=0.95), color="#475569")
        self.plotter.add_mesh(pv.Line((-3.25, 0.0, -0.28), (3.25, 0.0, -0.28)), color="#334155", line_width=3)
        self.spring_mesh = self._make_polyline(self._make_spring_points(self._horizontal_anchor, np.array([0.0, 0.0, 0.0])))
        self.plotter.add_mesh(self.spring_mesh, color="#38bdf8", line_width=4)
        self.string_mesh = None

    def _build_pendulum_scene(self) -> None:
        self.plotter.add_mesh(pv.Sphere(radius=0.08, center=self._pivot), color="#94a3b8", smooth_shading=True)
        self.plotter.add_mesh(pv.Line((-1.25, 0.0, self._pivot[2]), (1.25, 0.0, self._pivot[2])), color="#475569", line_width=3)
        self.string_mesh = self._make_polyline(np.array([self._pivot, self._pivot + np.array([0.0, 0.0, -self._length])]))
        self.plotter.add_mesh(self.string_mesh, color="#f8fafc", line_width=3)
        self.spring_mesh = None

    def _attach_interaction_observers(self) -> None:
        targets = [
            getattr(self.plotter, "iren", None),
            getattr(self.plotter, "interactor", None),
        ]
        seen = set()
        for target in targets:
            if target is None:
                continue
            if id(target) in seen:
                continue
            seen.add(id(target))
            self._add_observer(target, "LeftButtonPressEvent", self._on_left_press)
            self._add_observer(target, "MouseMoveEvent", self._on_mouse_move)
            self._add_observer(target, "LeftButtonReleaseEvent", self._on_left_release)

    @staticmethod
    def _add_observer(target, event_name: str, callback) -> None:
        if hasattr(target, "add_observer"):
            target.add_observer(event_name, callback)
        elif hasattr(target, "AddObserver"):
            target.AddObserver(event_name, callback)

    def _on_left_press(self, *_args) -> None:
        event_position = self._event_position()
        if event_position is None or not self._pick_mass(*event_position):
            return
        self._dragging = True
        self._last_drag_coordinate = self._current_coordinate
        self._last_drag_time = time.perf_counter()
        self._drag_velocity = 0.0
        QTimer.singleShot(0, self.drag_started.emit)

    def _on_mouse_move(self, *_args) -> None:
        if not self._dragging:
            return
        event_position = self._event_position()
        if event_position is None:
            return

        world = self._display_to_world_at_mass_depth(*event_position)
        if world is None:
            return

        coordinate = self._coordinate_from_world(world)
        now = time.perf_counter()
        dt = max(now - self._last_drag_time, 1.0e-4)
        self._drag_velocity = (coordinate - self._last_drag_coordinate) / dt
        self._current_coordinate = coordinate
        self._last_drag_coordinate = coordinate
        self._last_drag_time = now
        self._queue_visual_update(coordinate)
        QTimer.singleShot(0, lambda coordinate=coordinate, velocity=self._drag_velocity: self.drag_changed.emit(coordinate, velocity))

    def _on_left_release(self, *_args) -> None:
        if not self._dragging:
            return
        self._dragging = False
        coordinate = self._current_coordinate
        velocity = self._drag_velocity
        QTimer.singleShot(0, lambda: self.drag_released.emit(coordinate, velocity))

    def _event_position(self) -> tuple[int, int] | None:
        targets = [
            getattr(self.plotter, "iren", None),
            getattr(getattr(self.plotter, "iren", None), "interactor", None),
            getattr(self.plotter, "interactor", None),
        ]
        for target in targets:
            if target is None:
                continue
            if hasattr(target, "get_event_position"):
                return tuple(target.get_event_position())
            if hasattr(target, "GetEventPosition"):
                return tuple(target.GetEventPosition())
        return None

    def _pick_mass(self, x: int, y: int) -> bool:
        if self.mass_actor is None:
            return False
        world = self._display_to_world_at_mass_depth(x, y)
        if world is None:
            return False
        mass_position = self._mass_world_position(self._current_coordinate)
        distance = float(np.linalg.norm(world - mass_position))
        return distance <= self._sphere_radius * 1.5

    def _display_to_world_at_mass_depth(self, x: int, y: int) -> np.ndarray | None:
        renderer = self.plotter.renderer
        mass_position = self._mass_world_position(self._current_coordinate)
        renderer.SetWorldPoint(float(mass_position[0]), float(mass_position[1]), float(mass_position[2]), 1.0)
        renderer.WorldToDisplay()
        display_depth = renderer.GetDisplayPoint()[2]
        renderer.SetDisplayPoint(float(x), float(y), display_depth)
        renderer.DisplayToWorld()
        world = renderer.GetWorldPoint()
        if abs(world[3]) < 1.0e-12:
            return None
        return np.array(world[:3], dtype=float) / world[3]

    def _mass_world_position(self, coordinate: float) -> np.ndarray:
        if self._mode == "horizontal_spring":
            return np.array([coordinate, 0.0, 0.0], dtype=float)
        if self._mode == "pendulum":
            return self._pivot + np.array(
                [
                    self._length * sin(coordinate),
                    0.0,
                    -self._length * cos(coordinate),
                ],
                dtype=float,
            )
        return np.array([0.0, 0.0, -coordinate], dtype=float)

    def _coordinate_from_world(self, world: np.ndarray) -> float:
        if self._mode == "horizontal_spring":
            return float(np.clip(world[0], -2.55, 2.55))
        if self._mode == "pendulum":
            dx = world[0] - self._pivot[0]
            dz_down = self._pivot[2] - world[2]
            theta = atan2(dx, dz_down)
            return float(np.clip(theta, -pi * 0.88, pi * 0.88))
        return float(np.clip(-world[2], -2.25, 2.25))

    def _update_spring(self, start: np.ndarray, end: np.ndarray) -> None:
        if self.spring_mesh is None:
            return
        self._update_polyline(self.spring_mesh, self._make_spring_points(start, end))

    def _update_string(self, start: np.ndarray, end: np.ndarray) -> None:
        if self.string_mesh is None:
            return
        self._update_polyline(self.string_mesh, np.array([start, end], dtype=float))

    @staticmethod
    def _make_polyline(points: np.ndarray):
        mesh = pv.PolyData()
        mesh.points = np.asarray(points, dtype=float)
        mesh.lines = np.hstack([[len(points)], np.arange(len(points))]).astype(np.int_)
        return mesh

    @staticmethod
    def _update_polyline(mesh, points: np.ndarray) -> None:
        mesh.points = np.asarray(points, dtype=float)
        if hasattr(mesh, "Modified"):
            mesh.Modified()

    @staticmethod
    def _make_spring_points(start: np.ndarray, end: np.ndarray, coils: int = 11, count: int = 128) -> np.ndarray:
        start = np.asarray(start, dtype=float)
        end = np.asarray(end, dtype=float)
        axis = end - start
        length = np.linalg.norm(axis)
        if length < 1.0e-6:
            return np.repeat(start[None, :], count, axis=0)

        direction = axis / length
        helper = np.array([0.0, 0.0, 1.0]) if abs(direction[2]) < 0.85 else np.array([0.0, 1.0, 0.0])
        normal_a = np.cross(direction, helper)
        normal_a /= np.linalg.norm(normal_a)
        normal_b = np.cross(direction, normal_a)

        t = np.linspace(0.0, 1.0, count)
        phase = 2.0 * pi * coils * t
        radius = min(0.13, max(length * 0.045, 0.045))
        centerline = start + np.outer(t, axis)
        points = centerline + radius * np.outer(np.cos(phase), normal_a) + radius * np.outer(np.sin(phase), normal_b)
        points[0] = start
        points[-1] = end
        return points

    def _render(self) -> None:
        try:
            self.plotter.render()
        except Exception:
            pass

    def _schedule_render(self) -> None:
        if self.plotter is None or self._render_pending:
            return
        self._render_pending = True
        QTimer.singleShot(0, self._flush_render)

    def _flush_render(self) -> None:
        self._render_pending = False
        if self.plotter is not None:
            self._render()

    def _queue_visual_update(self, coordinate: float) -> None:
        self._pending_visual_coordinate = float(coordinate)
        if self._visual_update_pending:
            return
        self._visual_update_pending = True
        QTimer.singleShot(0, self._flush_visual_update)

    def _flush_visual_update(self) -> None:
        self._visual_update_pending = False
        coordinate = self._pending_visual_coordinate
        self._pending_visual_coordinate = None
        if coordinate is not None:
            self.update_visuals(coordinate)
