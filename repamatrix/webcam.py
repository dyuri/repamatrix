import time
import cv2
import numpy as np
import numpy.typing as npt
from mediapipe.python.solutions.selfie_segmentation import SelfieSegmentation
from blessed import Terminal
from .matrix import Configuration, get_colors, Screen, Overlay, Node, add_color

SPEED = .1


class WebcamOverlay(Overlay):

    def __init__(self, term, selfie_segmentation, cfg=None):
        cfg = cfg or {}

        super().__init__(term, "webcam", cfg)
        self._multiply = cfg.get("multiply", None)
        self._prop = cfg.get("prop", "color")
        self._selfie_segmentation = selfie_segmentation
        self._bgcolor = cfg.get("bgcolor", None)
        self._shade = cfg.get("shade", (64, 255, 0))
        self._shade_cutoff = cfg.get("shade_cutoff", 200)

    def _load(self, image=None):
        image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self._selfie_segmentation.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        condition = np.stack((results.segmentation_mask,) * 3, axis=-1) > 0.95
        bg_image = np.zeros(image.shape, dtype=np.uint8)
        output_image = np.where(condition, image, bg_image)
        output_image = cv2.resize(output_image, (self.width, self.height))
        output_image = cv2.cvtColor(output_image, cv2.COLOR_BGR2GRAY)

        self.img = output_image


    def _get_color(self, x, y):
        value = self.img[y, x]
        if value < self._shade_cutoff:
            color = tuple(int(value/self._shade_cutoff * c) for c in self._shade)
        else:
            color = tuple(int(c + (255-c) * (value-self._shade_cutoff)/(255-self._shade_cutoff)) for c in self._shade)
        if self._multiply is not None:
            color = tuple(int(self._multiply * component) for component in color)
        return color

    def get_node(self, x, y):
        color = self._get_color(x, y)
        cfg = {}
        cfg[self._prop] = color
        return Node(self.term, cfg)

    def mix(self, x, y, node):
        color = self._get_color(x, y)
        if color != (0, 0, 0):
            if self._prop == "color":
                mixcolor = add_color(node.color, color)
                tc = self.term.color_rgb(*mixcolor)
                nodestr = str(node)
                if nodestr != " ":
                    return tc + str(node)

                return " "
            elif self._prop == "bgcolor":
                return self.term.on_color_rgb(*color) + node.colored

        return self.term.normal + node.colored


def webcammatrix(config):
    term = Terminal()
    screen = Screen(config)
    cap = cv2.VideoCapture(config.get("camera", 0))
    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    update_time = config.get("update_time", config.get("speed", .1) / 10)

    key = None
    dx = 0
    with term.fullscreen(), term.cbreak(), term.hidden_cursor(), SelfieSegmentation(model_selection=1) as selfie_segmentation:
        overlay = WebcamOverlay(term, selfie_segmentation)
        screen._overlay = overlay
        try:
            while (key is None or key.code != term.KEY_ESCAPE) and cap.isOpened():
                success, image = cap.read()

                if not success:
                    continue

                overlay._load(image)

                if screen.step():
                    screen.display(dx)

                key = term.inkey(timeout=update_time, esc_delay=update_time / 10)

                if key.code == term.KEY_LEFT:
                    dx = (dx - 1) % term.width
                elif key.code == term.KEY_RIGHT:
                    dx = (dx + 1) % term.width

                time.sleep(update_time)
        except KeyboardInterrupt:
            pass


def main():
    config = Configuration()  # TODO
    config["colors"] = get_colors("green")

    config["status_message"] = "SMILE!"
    config["speed"] = SPEED
    config["fill"] = True

    webcammatrix(config)
