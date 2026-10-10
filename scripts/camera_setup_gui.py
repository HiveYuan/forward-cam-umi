"""Keyboard-driven role binding with exactly one selected-camera preview.

Qt owns selection and navigation; PreviewSession owns the capture process.
Identity confirmation and full-resolution mode validation remain separate.
"""
import signal
import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QFrame, QVBoxLayout,
                              QHBoxLayout, QListWidget, QListWidgetItem,
                              QPushButton, QDoubleSpinBox)

from camera_config import (CameraBinding, CameraSpec, CaptureMode, CaptureSource,
                           ROLES, normalize_image, save_config, supported_frame_rate)
from camera_preview import PreviewSession
from camera_setup_options import (ROLE_LABELS, ROLE_HINTS, GUIDE_MODES,
                                  identity_preview_mode, preferred_fps)


class ChoiceList(QListWidget):
    accepted = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accepted.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class CameraPreview(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("cameraPreview")
        self.setStyleSheet("QFrame#cameraPreview { background: #162132; border: 1px solid #344760; border-radius: 10px; }")
        self.token = None
        layout = QVBoxLayout(self)
        self.name = QLabel()
        self.name.setWordWrap(True)
        self.name.setStyleSheet("font-size: 19px; font-weight: 600;")
        self.identity = QLabel()
        self.identity.setStyleSheet("color: #a6b4c8;")
        self.identity.setWordWrap(True)
        self.identity.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumSize(360, 240)
        self.image.setStyleSheet("background: #080e19; border-radius: 6px;")
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.name)
        layout.addWidget(self.identity)
        layout.addWidget(self.image, 1)
        layout.addWidget(self.status)

    def refresh(self, info, state, rotation, status):
        self.name.setText(info["name"] if info else "Camera preview")
        self.identity.setText(info["device_id"] if info else "")
        self.status.setText(status)
        # Never display another device's image under the newly selected name.
        if (info is None or state is None or state.source.device_id != info["device_id"]
                or not state.live):
            self.image.clear()
            self.image.setText("Unavailable" if state and state.error else "No live preview")
            self.token = None
            return
        token = (state.source, state.last_frame, rotation, self.image.width(), self.image.height())
        if token == self.token:
            return
        # Identity frames are raw; validation frames are already normalized.
        extra_rotation = (rotation - state.source.rotation_degrees) % 360
        pixels = normalize_image(state.image, extra_rotation)
        height, width = pixels.shape[:2]
        image = QImage(pixels.data, width, height, pixels.strides[0], QImage.Format.Format_BGR888).copy()
        self.image.setPixmap(QPixmap.fromImage(image).scaled(
            self.image.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        self.token = token


class CameraWizard(QWidget):
    SWITCH_DELAY_MS = 180

    def __init__(self, inventory, args, session=None):
        super().__init__()
        self.inventory = inventory
        self.by_id = {info["device_id"]: info for info in inventory}
        if len(self.by_id) != len(inventory):
            raise ValueError("camera inventory has duplicate device IDs")
        self.args = args
        self.session = session if session is not None else PreviewSession()
        self.bindings = {}
        self.specs = []
        self.result = None
        self.stage = "identity"
        self.role_index = 0
        self.mode_index = 0
        self.pending_id = None
        self.pending_spec = None
        self.requested_source = None
        self.start_error = ""
        self.rotation = 0
        self.closed = False
        # Debounce arrow repeats without leaving the previous camera open.
        self.switch_timer = QTimer(self)
        self.switch_timer.setSingleShot(True)
        self.switch_timer.timeout.connect(self._start_requested_preview)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self._build_ui()
        self._identity()
        self.timer.start(80)

    def _build_ui(self):
        self.setWindowTitle("UMI · Camera setup")
        self.resize(1180, 800)
        self.setMinimumSize(940, 660)
        self.setStyleSheet("""
            QWidget { background: #0d1523; color: #e8eef7; font-size: 13px; }
            QLabel { background: transparent; }
            QListWidget { background: #162132; border: 1px solid #344760; border-radius: 8px; }
            QListWidget::item { padding: 12px 10px; border-bottom: 1px solid #28374b; }
            QListWidget::item:selected { background: #254f79; color: white; }
            QListWidget::item:disabled { color: #66788e; }
            QPushButton { background: #22344c; border: 1px solid #425b7d; border-radius: 7px; padding: 10px; }
            QPushButton:focus { border: 2px solid #89c8ff; }
            QPushButton:disabled { color: #718197; background: #1a2739; }
            QPushButton#primary { background: #28689f; font-weight: 600; }
            QDoubleSpinBox { background: #162132; border: 1px solid #425b7d; padding: 8px; }
        """)
        outer = QVBoxLayout(self)
        heading = QLabel("CAMERA SETUP")
        heading.setStyleSheet("font-size: 22px; font-weight: 700;")
        outer.addWidget(heading)
        caption = QLabel(f"{len(self.inventory)} devices · Preview follows selection · One camera open at a time")
        caption.setStyleSheet("color: #a6b4c8;")
        outer.addWidget(caption)
        body = QHBoxLayout()
        outer.addLayout(body, 1)
        panel = QWidget()
        panel.setFixedWidth(390)
        left = QVBoxLayout(panel)
        left.setContentsMargins(0, 8, 8, 0)
        self.title = QLabel()
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size: 21px; font-weight: 600;")
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: #b7c6da;")
        self.choices = ChoiceList()
        self.choices.setMinimumHeight(150)
        self.choices.currentRowChanged.connect(self.selection_changed)
        self.choices.accepted.connect(self.advance)
        self.choices.itemDoubleClicked.connect(lambda _: self.advance())
        self.fps = QDoubleSpinBox()
        self.fps.setPrefix("FPS  ")
        self.fps.setDecimals(6)
        self.fps.setSingleStep(1)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet("color: #f2c578;")
        self.next_button = QPushButton()
        self.next_button.setObjectName("primary")
        self.next_button.setAutoDefault(True)
        self.next_button.clicked.connect(self.advance)
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        self.retry_button = QPushButton("Retry selected camera")
        self.retry_button.clicked.connect(self.retry_preview)
        cancel = QPushButton("Close / cancel")
        cancel.clicked.connect(self.close)
        left.addWidget(self.title)
        left.addWidget(self.hint)
        left.addWidget(self.choices, 1)
        self.spacer = QWidget()
        left.addWidget(self.spacer, 1)
        left.addWidget(self.fps)
        left.addWidget(self.notice)
        left.addWidget(self.next_button)
        left.addWidget(self.retry_button)
        navigation = QHBoxLayout()
        navigation.addWidget(self.back_button)
        navigation.addWidget(cancel)
        left.addLayout(navigation)
        body.addWidget(panel)
        self.preview = CameraPreview()
        body.addWidget(self.preview, 1)
        footer = QLabel("↑ / ↓ Preview a camera   ·   Enter Confirm   ·   Esc Back   ·   No video is recorded")
        footer.setStyleSheet("color: #98adc7; padding: 8px;")
        outer.addWidget(footer)
        QShortcut(QKeySequence("Escape"), self, activated=self.go_back)

    def _screen(self, stage, title, hint, button, options=(), selected=0):
        self.stage = stage
        self.title.setText(title)
        self.hint.setText(hint)
        self.notice.clear()
        self.next_button.setText(button)
        self.next_button.setEnabled(True)
        self.choices.blockSignals(True)
        self.choices.clear()
        for text, value, enabled in options:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, value)
            if not enabled:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.choices.addItem(item)
        self.choices.setVisible(bool(options))
        self.spacer.setVisible(not options)
        self.choices.setCurrentRow(selected if options else -1)
        self.choices.blockSignals(False)
        self.fps.setVisible(stage == "mode")
        self.retry_button.setVisible(stage in ("identity", "rotation", "validate"))
        self.back_button.setEnabled(stage != "done" and not (stage == "identity" and self.role_index == 0))
        self.selection_changed()
        (self.choices if options else self.next_button).setFocus()

    def selected(self):
        item = self.choices.currentItem()
        if item is None or not item.flags() & Qt.ItemFlag.ItemIsEnabled:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _stop_preview(self):
        self.switch_timer.stop()
        self.requested_source = None
        self.start_error = ""
        self.session.close()

    def _request_preview(self, source):
        if self.closed or source == self.requested_source:
            return
        self._stop_preview()
        self.requested_source = source
        self.switch_timer.start(self.SWITCH_DELAY_MS)

    def _start_requested_preview(self):
        if self.closed or self.requested_source is None:
            return
        try:
            self.session.start(self.requested_source)
        except Exception as exc:
            self.start_error = str(exc)
        self.tick()

    def retry_preview(self):
        if self.closed or self.requested_source is None:
            return
        source = self.requested_source
        self._stop_preview()
        self._request_preview(source)
        self.tick()

    def _identity(self, selected_id=None):
        role = ROLES[self.role_index]
        used = {binding.device_id for binding in self.bindings.values()}
        options = [(f"{i['name']}\n{i['device_id']}" + (" · already assigned" if i['device_id'] in used else ""),
                    i['device_id'], i['device_id'] not in used) for i in self.inventory]
        if role == "b0587b" and not self.args.require_head:
            options.append(("Skip optional head camera", "skip", True))
        first = next((i for i, option in enumerate(options) if option[2]), 0)
        selected = next((i for i, option in enumerate(options) if option[1] == selected_id and option[2]), first)
        self._screen("identity", f"1/2 · {ROLE_LABELS[role]}", ROLE_HINTS[role]
                     + "\nHighlight a device to preview it, then press Enter.", "Select camera", options, selected)

    def _mode(self):
        self._stop_preview()
        self.pending_spec = None
        binding = list(self.bindings.values())[self.mode_index]
        self.pending_id = binding.device_id
        suggested = GUIDE_MODES[binding.role]
        ranges = sorted(set(self.by_id[binding.device_id]["modes"]), reverse=True)
        options, recommendation = [], None
        for i, (w, h, low, high) in enumerate(ranges):
            recommended = ((w, h) == (suggested.width, suggested.height)
                           and supported_frame_rate(suggested.fps, low, high) is not None)
            if recommended and recommendation is None:
                recommendation = i
            text = f"{w} × {h}  ·  {low:.6g}–{high:.6g} fps"
            options.append((text + ("\nGuide suggestion" if recommended else ""), (w, h, low, high), True))
        self._screen("mode", f"2/2 · {ROLE_LABELS[binding.role]}",
                     "Select capture resolution and FPS, then press Enter to test this mode.",
                     "Test selected mode", options, recommendation or 0)
        if recommendation is None:
            self.notice.setText("Guide settings are unavailable on this device. Choose a supported alternative.")

    def selection_changed(self, *_):
        value = self.selected()
        if self.stage == "identity":
            self.pending_id = None if value == "skip" else value
            if self.pending_id is None:
                self._stop_preview()
            else:
                info = self.by_id[self.pending_id]
                try:
                    mode = identity_preview_mode(info["modes"], max_width=640, max_height=480, fps=15)
                    self._request_preview(CaptureSource(self.pending_id, info["name"], mode.width, mode.height, mode.fps))
                except Exception as exc:
                    self._stop_preview()
                    self.start_error = str(exc)
        elif self.stage == "rotation" and value is not None:
            self.rotation = value
        elif self.stage == "mode" and value is not None:
            _, _, low, high = value
            binding = list(self.bindings.values())[self.mode_index]
            self.fps.setRange(low, high)
            self.fps.setValue(preferred_fps(low, high, GUIDE_MODES[binding.role].fps))
        self.tick()

    def _selected_state(self):
        state = self.session.state
        if state is not None and state.source == self.requested_source and state.source.device_id == self.pending_id:
            return state
        return None

    def update_gate(self):
        state = self._selected_state()
        self.retry_button.setEnabled(self.requested_source is not None)
        if self.stage in ("identity", "rotation"):
            skip = self.stage == "identity" and self.selected() == "skip"
            self.next_button.setEnabled(skip or (state is not None and state.live))
        elif self.stage == "mode":
            self.next_button.setEnabled(self.selected() is not None)
        elif self.stage == "validate":
            ready = (state is not None and state.live and state.first_frame is not None
                     and time.monotonic() - state.first_frame >= self.args.seconds)
            self.next_button.setEnabled(ready)
            error = self.start_error or (state.error if state else "")
            if error:
                self.notice.setText(error + "\nRetry this camera or use Back to choose another mode.")
            elif ready:
                self.notice.setText("Source and delivered dimensions verified. Confirm the view and direction. "
                                    "Recording FPS and synchronization remain unverified.")
            else:
                self.notice.setText(f"Waiting for a live preview for {self.args.seconds:g} seconds…")

    def advance(self):
        self.update_gate()
        if not self.next_button.isEnabled():
            return
        if self.stage == "identity":
            if self.selected() == "skip":
                self._next_identity()
                return
            self.rotation = 0
            role = ROLES[self.role_index]
            self._screen("rotation", f"Confirm · {ROLE_LABELS[role]}",
                         "Cover this physical lens to verify the preview. Choose the rotation that makes its view upright.",
                         "Confirm camera & direction", [("0° · Keep image direction", 0, True),
                                                         ("180° · Turn upside-down image upright", 180, True)])
        elif self.stage == "rotation":
            info = self.by_id[self.pending_id]
            role = ROLES[self.role_index]
            self.bindings[role] = CameraBinding(role, self.pending_id, info["name"], self.rotation)
            self._next_identity()
        elif self.stage == "mode":
            w, h, low, high = self.selected()
            if supported_frame_rate(self.fps.value(), low, high) is None:
                self.notice.setText("Choose an FPS within the supported range.")
                return
            binding = list(self.bindings.values())[self.mode_index]
            self.pending_spec = CameraSpec.from_binding(binding, CaptureMode(w, h, self.fps.value()))
            self._request_preview(self.pending_spec.source())
            self._screen("validate", "Check capture mode",
                         f"{ROLE_LABELS[binding.role]}\n{w} × {h} · {self.fps.value():g} fps · rotate {binding.rotation_degrees}°",
                         "Confirm capture mode")
        elif self.stage == "validate":
            self.specs.append(self.pending_spec)
            self.mode_index += 1
            if self.mode_index < len(self.bindings):
                self._mode()
            else:
                self._stop_preview()
                self.pending_id = None
                summary = "\n\n".join(f"{ROLE_LABELS[s.role]}\n{s.device_id}\n"
                                        f"{s.width} × {s.height} · {s.fps:g} fps · {s.rotation_degrees}°"
                                        for s in self.specs)
                self._screen("review", "Ready to save", summary, "Save configuration")
        elif self.stage == "review":
            try:
                save_config(self.args.config, self.specs)
            except (OSError, ValueError) as exc:
                self.notice.setText(str(exc))
                return
            self.result = list(self.specs)
            self._screen("done", "Camera setup saved", str(self.args.config)
                         + "\n\nNext: focus and intrinsics. Session recording is not yet implemented on macOS.", "Close")
        elif self.stage == "done":
            self.close()

    def _next_identity(self):
        self.role_index += 1
        if self.role_index < len(ROLES):
            self._identity()
        else:
            self.mode_index = 0
            self._mode()

    def _edit_identity(self, index):
        self.role_index = index
        previous = self.bindings.get(ROLES[index])
        for role in ROLES[index:]:
            self.bindings.pop(role, None)
        self.specs.clear()
        self.mode_index = 0
        self._identity(previous.device_id if previous else None)

    def go_back(self):
        if self.stage == "rotation":
            self._identity(self.pending_id)
        elif self.stage == "validate":
            self._mode()
        elif self.stage in ("mode", "review") and self.mode_index > 0:
            self.mode_index -= 1
            self.specs.pop()
            self._mode()
        elif self.stage == "mode":
            self._edit_identity(len(ROLES) - 1)
        elif self.stage == "identity" and self.role_index > 0:
            self._edit_identity(self.role_index - 1)
        else:
            self.close()

    def tick(self):
        if self.closed:
            return
        self.session.poll()
        state = self._selected_state()
        binding = next((b for b in self.bindings.values() if b.device_id == self.pending_id), None)
        rotation = self.rotation if self.stage == "rotation" else (binding.rotation_degrees if binding else 0)
        if self.start_error:
            status = self.start_error
        elif state is not None and state.error:
            status = state.error
        elif state is not None and state.live:
            status = f"Live · {state.source.width} × {state.source.height} · rotate {rotation}°"
        elif self.requested_source is not None:
            status = "Connecting to the selected camera…"
        elif self.stage == "mode":
            status = "Press Enter to test the selected capture mode."
        else:
            status = "Preview stopped."
        self.preview.refresh(self.by_id.get(self.pending_id), state, rotation, status)
        self.update_gate()

    def closeEvent(self, event):
        self.closed = True
        self.timer.stop()
        self._stop_preview()
        event.accept()


def run_wizard(inventory, args):
    if args.config.exists():
        raise ValueError(f"{args.config} already exists; archive it or use --config with a new path")
    from camera_macos import request_camera_access
    request_camera_access()
    app = QApplication.instance() or QApplication([])
    window = CameraWizard(inventory, args)
    old_handler = signal.signal(signal.SIGINT, lambda *_: window.close())
    try:
        window.show()
        app.exec()
    finally:
        window.close()
        signal.signal(signal.SIGINT, old_handler)
    if window.result is None:
        raise KeyboardInterrupt
    print(f"Saved local bindings: {args.config}")
    return window.result
