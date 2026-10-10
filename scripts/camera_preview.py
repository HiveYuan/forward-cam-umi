"""One isolated preview worker for the setup UI, never for recording.

Switching devices releases the previous worker before starting another.
Native startup/teardown can block, so capture runs in a disposable process.
AVFoundation and Qt are not imported in the parent by this module.
"""
from dataclasses import dataclass, field
import multiprocessing as mp
import queue
import time


def capture_worker(source, stop, frames, events):
    # Imports stay inside the spawned worker; native camera objects never cross
    # process boundaries. Authorization is checked by PreviewCapture as usual.
    import cv2
    from camera_macos import PreviewCapture

    frames.cancel_join_thread()  # Closing a window must not wait for queued images.
    try:
        with PreviewCapture(source) as capture:
            last_sent = 0.0
            while not stop.is_set():
                frame = capture.read(timeout=10)
                now = time.monotonic()
                if now - last_sent < 0.1:
                    continue
                height, width = frame.image.shape[:2]
                scale = min(1, 960 / width, 600 / height)
                thumb = cv2.resize(frame.image, None, fx=scale, fy=scale,
                                   interpolation=cv2.INTER_AREA)
                try:
                    frames.put_nowait((now, thumb))
                    last_sent = now
                except queue.Full:
                    pass  # Bounded UI thumbnails, explicitly not recording frames.
    except Exception as exc:
        events.send(str(exc))
    finally:
        events.close()


@dataclass
class PreviewState:
    source: object
    process: object
    stop: object
    frames: object
    events: object
    started: float = field(default_factory=time.monotonic)
    first_frame: float | None = None
    last_frame: float | None = None
    image: object = None
    error: str = ""
    released: bool = False

    @property
    def live(self):
        return not self.error and self.last_frame is not None and time.monotonic() - self.last_frame < 3


class PreviewSession:
    def __init__(self, worker_target=capture_worker, startup_timeout=20):
        self.context = mp.get_context("spawn")
        self.worker_target = worker_target
        self.startup_timeout = startup_timeout
        self.state = None

    def start(self, source):
        self.close()
        stop = self.context.Event()
        frames = self.context.Queue(maxsize=2)
        receive, send = self.context.Pipe(duplex=False)
        process = self.context.Process(target=self.worker_target,
                                       args=(source, stop, frames, send), daemon=True)
        state = PreviewState(source, process, stop, frames, receive)
        try:
            process.start()
        except Exception:
            receive.close()
            frames.close()
            raise
        finally:
            send.close()
        self.state = state

    def poll(self):
        now = time.monotonic()
        state = self.state
        if state is None or state.error:
            return state
        try:
            while state.events.poll():
                state.error = state.events.recv()
        except EOFError:
            pass
        try:
            while True:
                timestamp, state.image = state.frames.get_nowait()
                state.last_frame = timestamp
                if state.first_frame is None:
                    state.first_frame = timestamp
        except queue.Empty:
            pass
        if not state.error:
            if not state.process.is_alive():
                state.error = "Camera worker stopped. Retry this camera."
            elif state.last_frame is None and now - state.started > self.startup_timeout:
                state.error = "No preview received. Check camera connection/access and retry."
            elif state.last_frame is not None and now - state.last_frame > 3:
                state.error = "Preview stopped updating. Check connection and retry."
        if state.error:
            self._release(state)
        return state

    @staticmethod
    def _release(state):
        if state.released:
            return
        state.stop.set()
        state.process.join(timeout=0.1)
        if state.process.is_alive():
            state.process.terminate()
            state.process.join(timeout=0.2)
        if state.process.is_alive():
            state.process.kill()
            state.process.join(timeout=0.2)
        if state.process.is_alive():
            raise RuntimeError("Previous camera has not stopped; cannot open another camera yet.")
        state.frames.close()
        state.events.close()
        state.released = True

    def close(self):
        if self.state is not None:
            self._release(self.state)
            self.state = None
