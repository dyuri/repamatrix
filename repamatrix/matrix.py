from blessed import Terminal
import datetime
import time
import signal
import random


CHARSET = {
    "greek": "αβγδεζηθικλμνξοπρστυφχψως",
    "greek_c": "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ",
    "japan": "ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ",
    "letters": "qwertyuiopasdfghjklzxcvbnm",
    "letters_c": "QWERTYUIOPASDFGHJKLZXCVBNM",
    "numbers": "1234567890",
}

CHARSET["default"] = CHARSET["japan"] + CHARSET["greek"]


def make_colors(base, n=7):
    colors = []
    for i in range(n):
        color = tuple(cv // n * i for cv in base)
        colors.append(color)

    colors.append((255, 255, 255))
    return colors


PALETTE = {
    "default": [
        (9, 37, 0),
        (14, 75, 0),
        (28, 109, 0),
        (37, 146, 0),
        (46, 182, 0),
        (55, 218, 0),
        (64, 255, 0),
        (228, 255, 219),
    ],
    "bw": make_colors((255, 255, 255)),
    "red" : make_colors((255, 0, 0)),
    "green" : make_colors((0, 255, 0)),
    "blue" : make_colors((0, 0, 255)),
    "cyan" : make_colors((0, 255, 255)),
    "magenta" : make_colors((255, 0, 255)),
    "yellow" : make_colors((255, 255, 0)),
    "purple" : make_colors((128, 0, 255)),
}

PALETTE["default"] = PALETTE["cyan"]

def add_color(c1, c2):
    if c1 is None:
        return c2
    elif c2 is None:
        return c1

    return tuple(min(255, v1 + v2) for v1, v2 in zip(c1, c2))


class Configuration(dict):
    pass


class Node:

    def __init__(self, term, config):
        self.term = term
        self.config = config
        self._color = config.get("color", None)
        self._bgcolor = config.get("bgcolor", None)
        self._char = config.get("char", " ")
        self._term_color = ""

    @property
    def term_color(self):
        if self.term:
            if not self._term_color:
                if not self._color and not self._bgcolor:
                    self._term_color = self.term.normal
                else:
                    tc = ""
                    if self._bgcolor:
                        tc += self.term.on_color_rgb(*self._bgcolor)
                    if self._color:
                        tc += self.term.color_rgb(*self._color)
        return self._term_color

    @property
    def color(self):
        return self._color

    @property
    def bgcolor(self):
        return self._bgcolor

    @property
    def colored(self):
        return self.term_color + str(self)

    def __str__(self):
        return self._char


EMPTYNODE = Node(None, {})


class DynamicNode(Node):

    def __init__(self, term, config):
        self.term = term
        self.config = config
        self._colors = config.get("colors", get_colors())
        self._color = None
        self._charset = config.get("charset", CHARSET["default"])
        self._char = config.get("char", random.choice(self._charset))
        self._lifetime = config.get("lifetime", None)
        self._age = 0

    @property
    def term_color(self):
        return self.term.color_rgb(*self.color)

    @property
    def color(self):
        if not self._color:
            self._color = random.choice(self._colors[1:-1])
        return self._color

    def __str__(self):
        if self._lifetime is not None and self._lifetime < self._age:
            return self._char

        self._age += 1
        return self._char


class FadingNode(DynamicNode):

    def __init__(self, term, config):
        super().__init__(term, config)
        self._target_color = random.randint(1, len(self._colors) - 2)
        usewhites = self.config.get("usewhites", None)
        self._current_color = len(self._colors) - (1 if usewhites else 2)

    @property
    def color(self):
        cidx = self._current_color
        if self._target_color < self._current_color:
            self._current_color -= 1

        if self._lifetime is not None and self._lifetime < self._age + cidx:
            cidx = max(0, self._lifetime - self._age)

        return self._colors[cidx]


class FadingFlasher(FadingNode):
    def __str__(self):
        if self._lifetime is not None and self._lifetime > self._age:
            self._char = random.choice(self._charset)
        return super().__str__()


class Spawner:

    def __init__(self, height, term, config):
        self.height = height
        self.term = term
        self.config = config
        self._nodecls = DynamicNode

        self.nodecfg = self.config.copy()
        self.nodecfg["lifetime"] = self.get_lifetime()

        usewhites = self.config.get("usewhites", None)
        if usewhites in [True, False]:
            self.nodecfg["usewhites"] = usewhites
        else:
            self.nodecfg["usewhites"] = random.choice([True, False])

        self.pos = 0

    @property
    def nodecls(self):
        return self._nodecls

    def get_lifetime(self):
        lifetime = self.config.get("lifetime", None)

        if lifetime is None:
            lifetime = int(self.height * (.5 + random.random()))

        return lifetime

    def next_node(self):
        return self.nodecls(self.term, self.nodecfg)

    def step(self, column):
        column[self.pos] = self.next_node()

        self.pos += 1
        if self.pos >= self.height:
            return None

        return self


class FadingSpawner(Spawner):

    def __init__(self, height, term, config):
        super().__init__(height, term, config)
        self._nodecls = FadingNode


class FadingFlasherSpawner(FadingSpawner):

    @property
    def nodecls(self):
        if random.random() < .01:
            return FadingFlasher
        else:
            return FadingNode


class Eraser(Spawner):

    def next_node(self):
        return EMPTYNODE


class Column:

    def __init__(self, height, term, config):
        self.height = height
        self.term = term
        self.config = config

        self._nodes = []
        self._clear()
        self._spawner = None
        self._spawner_classes = [FadingSpawner, FadingFlasherSpawner]  # Spawner, FadingSpawner, FadingFlasherSpawner, Eraser

        if config.get("fill", False):
            self._fill()

    def _clear(self):
        self._nodes = [EMPTYNODE for _ in range(self.height)]

    def __getitem__(self, y):
        if len(self._nodes) > y:
            return self._nodes[y]
        return EMPTYNODE

    def __setitem__(self, y, node):
        if len(self._nodes) > y:
            self._nodes[y] = node

    def _fill(self):
        self._spawner = self.spawn(1)

    def get_spawner(self):
        return random.choice(self._spawner_classes)

    def spawn(self, probability=None):
        if probability is None:
            probability = self.config.get("spawn_probability", .01)

        if random.random() < probability:
            spawnercls = self.get_spawner()
            return spawnercls(self.height, self.term, self.config)
        else:
            return None

    def step(self):
        if self._spawner:
            self._spawner = self._spawner.step(self)
        else:
            self._spawner = self.spawn()


class Overlay:

    def __init__(self, term, content=None, cfg=None):
        self.term = term
        self.width = term.width
        self.height = term.height
        self.content = content
        self.config = cfg or {}

    def get_node(self, x, y):
        return EMPTYNODE

    def mix(self, x, y, node):
        return node.colored


class ImageOverlay(Overlay):

    def __init__(self, term, image, cfg=None):
        try:
            from PIL import Image
            self._Image = Image
        except ModuleNotFoundError:
            raise ModuleNotFoundError("Install PIL for ImageOverlay support!")
        cfg = cfg or {}

        super().__init__(term, image, cfg)
        self._multiply = cfg.get("multiply", None)
        self._prop = cfg.get("prop", "color")
        self._load()

    def _load(self):
        oimg = self._Image.open(self.content)
        oimg = oimg.convert("RGB")
        oimg.thumbnail((self.width, 2 * self.height))
        self.img = oimg.resize((oimg.width, oimg.height // 2))
        self._imgdata = list(oimg.getdata())
        self._top = int((self.height - (oimg.height // 2)) / 2)
        self._before = int((self.width - oimg.width) / 2)

    def _get_color(self, x, y):
        _x = x - self._before
        _y = y - self._top
        if 0 <= _x < self.img.width and 0 <= _y < self.img.height:
            # color = self.img.getpixel((_x, _y))
            idx = _x + 2 * _y * self.img.width
            color = self._imgdata[idx]
            if self._multiply is not None:
                color = tuple(int(self._multiply * component) for component in color)
            return color
        return (0, 0, 0)

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


class TextOverlay(Overlay):

    def __init__(self, term, content, cfg=None):
        super().__init__(term, content, cfg)

        self._cheight = len(content)
        self._cwidth = len(content[0])
        self._top = int((self.height - self._cheight) / 2)
        self._bottom = self._top + self._cheight
        self._before = int((self.width - self._cwidth) / 2)
        self._after = self._before + self._cwidth
        self.default_color = self.config.get("default_color", (0, 64, 64))
        self.color_map = self.config.get("color_map", CMAP)

        self._content = self._process_content(content)

    def _get_color(self, ch):
        return self.color_map.get(ch, self.default_color)

    def _process_content(self, content):
        return [
            Node(self.term, {"char": ch, "color": self._get_color(ch)})
            if ch != " " else None
            for ch in "".join(content)
        ]

    def get_node(self, x, y):
        if self._top <= y < self._bottom and self._before <= x < self._after:
            local_y = y - self._top
            local_x = x - self._before
            return self._content[self._cwidth * local_y + local_x]
        else:
            return None

    def mix(self, x, y, node):
        onode = self.get_node(x, y)
        if onode and onode.color:
            color = add_color(node.color, onode.color)
            tc = self.term.color_rgb(*color)
            nodestr = str(node)
            if nodestr != " ":
                return tc + str(onode)

            return " "
        return node.colored


class Screen:

    def __init__(self, config=None):
        self.term = Terminal()
        self.config = config or {}

        self.step_time = config.get("speed", .1)
        self.status_message = config.get("status_message", "M4TR1X")

        self._notes = []

        self._configure()

        signal.signal(signal.SIGWINCH, self._resize_handler())

    def _configure(self):
        self.width = self.config.get("width", self.term.width)
        self.height = self.config.get("height", self.term.height - 1)

        self._last_step = 0
        self._overlay = None
        self._columns = self._init_columns()

    def _init_columns(self):
        return [Column(self.height, self.term, self.config) for _ in range(self.width)]

    def _resize_handler(self):
        def on_resize(*_):
            print(self.term.clear)
            self._configure()
        return on_resize

    def status(self, message=None):
        message = message or self.status_message
        left_txt = self._notes[-1] if len(self._notes) else message
        now = datetime.datetime.now().time()
        right_txt = now.strftime("%H:%M:%S")

        term = self.term
        colors = self.colors

        msg = (
            term.normal
            + term.on_color_rgb(*colors[0])
            + term.color_rgb(*colors[-1])
            + term.clear_eol
            + left_txt
            + term.rjust(right_txt, term.width - len(left_txt))
        )
        with term.location(0, term.height - 1):
            print(msg, end="")

    @property
    def overlay(self):
        if not self._overlay:
            if "overlay_image" in self.config:
                try:
                    self._overlay = ImageOverlay(self.term, self.config["overlay_image"], {"multiply": .75, "prop": "color"})
                except:
                    self._notes.append("ImageOverlay could not be initialized, do you have pillow installed?")
            elif "overlay_text" in self.config:
                self._overlay = TextOverlay(self.term, self.config["overlay_text"])

            if not self._overlay:
                self._overlay = Overlay(self.term)

        return self._overlay

    @property
    def colors(self):
        return self.config.get("colors", PALETTE["default"])

    @property
    def columns(self):
        return self._columns

    @property
    def lines(self):
        return [self.line(y) for y in range(self.height)]

    def column(self, x):
        return self._columns[x]

    def line(self, y):
        return [c[y] for c in self._columns]

    def step(self):
        now = time.time()
        if self._last_step + self.step_time < now:
            self._last_step = now
            for column in self._columns:
                column.step()
            return True

        return False

    def mix_overlay(self, x, y, node):
        if self.overlay:
            return self.overlay.mix(x, y, node)

        return node

    def __getitem__(self, x):
        return self._columns[x]

    def __str__(self):
        return self.display()

    def _display(self, dx=0):
        image = []
        for y in range(self.height):
            line = []
            for x in range(self.width):
                mx = (x - dx) % self.term.width
                try:
                    node = self.mix_overlay(x, y, self[mx][y])
                    if "force_bgcolor" in self.config:
                        node._bgcolor = self.config["force_bgcolor"]
                    line.append(node)
                except Exception:
                    pass

            image.append("".join(line))

        return "\n".join(image)

    def display(self, dx=0):
        print(self.term.move_xy(0, 0) + self._display(dx), end="")
        self.status()


def get_colors(palette="default"):
    return PALETTE[palette]


def matrix(config):
    term = Terminal()
    screen = Screen(config)

    update_time = config.get("update_time", config.get("speed", .1) / 10)

    key = None
    dx = 0
    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        try:
            while key is None or key.code != term.KEY_ESCAPE:
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
