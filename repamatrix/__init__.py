from blessed import Terminal
import platform
import getpass
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


PALETTE = {
    "green": [
        (9, 37, 0),
        (14, 75, 0),
        (28, 109, 0),
        (37, 146, 0),
        (46, 182, 0),
        (55, 218, 0),
        (64, 255, 0),
        (228, 255, 219),
    ]
}

PALETTE["default"] = PALETTE["green"]

SPEED = .1
UPDATE_TIME = SPEED / 10

OVERLAY = [
    "     █████                                  ███ ",
    "    ▒▒███                                  ▒▒▒  ",
    "  ███████  █████ ████ █████ ████ ████████  ████ ",
    " ███▒▒███ ▒▒███ ▒███ ▒▒███ ▒███ ▒▒███▒▒███▒▒███ ",
    "▒███ ▒███  ▒███ ▒███  ▒███ ▒███  ▒███ ▒▒▒  ▒███ ",
    "▒███ ▒███  ▒███ ▒███  ▒███ ▒███  ▒███      ▒███ ",
    "▒▒████████ ▒▒███████  ▒▒████████ █████     █████",
    " ▒▒▒▒▒▒▒▒   ▒▒▒▒▒███   ▒▒▒▒▒▒▒▒ ▒▒▒▒▒     ▒▒▒▒▒ ",
    "            ███ ▒███                            ",
    "           ▒▒██████                             ",
    "            ▒▒▒▒▒▒                              ",
]
CMAP = {
    "▒": (32, 32, 64),
    "█": (64, 64, 128),
}


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
        self._char = config.get("char", " ")

    @property
    def term_color(self):
        if self.term:
            if not self._color:
                return self.term.normal
            return self.term.color_rgb(*self._color)
        return ""

    @property
    def color(self):
        return self._color

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

    def _clear(self):
        self._nodes = [EMPTYNODE for _ in range(self.height)]

    def __getitem__(self, y):
        return self._nodes[y]

    def __setitem__(self, y, node):
        self._nodes[y] = node

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

    def __init__(self, term, content):
        self.term = term
        self.width = term.width
        self.height = term.height
        self.content = content
        self._cheight = len(content)
        self._cwidth = len(content[0])
        self._top = int((self.height - self._cheight) / 2)
        self._bottom = self._top + self._cheight
        self._before = int((self.width - self._cwidth) / 2)
        self._after = self._before + self._cwidth
        self._content = "".join(content)
        # TODO convert _content to nodes here

    def get_node(self, x, y):
        if self._top <= y < self._bottom and self._before <= x < self._after:
            local_y = y - self._top
            local_x = x - self._before
            char = self._content[self._cwidth * local_y + local_x]
            if char == " ":
                return None
            return Node(self.term, {"char": char, "color": CMAP.get(char, (0, 0, 0))})
        else:
            return None


class Screen:

    def __init__(self, width=80, height=24, term=None, config=None):
        self.term = None
        self.config = {}
        self.configure(width, height, term, config)

    def configure(self, width=None, height=None, term=None, config=None):
        if term is not None:
            self.term = term
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        if config is not None:
            self.config = config

        self.step_time = SPEED  # TODO
        self._last_step = 0
        self._overlay = None
        self._columns = self._init_columns()

    def _init_columns(self):
        return [Column(self.height, self.term, self.config) for _ in range(self.width)]

    @property
    def overlay(self):
        if not self._overlay and "overlay" in self.config:
            self._overlay = Overlay(self.term, self.config["overlay"])
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

    def get_overlay_node(self, x, y):
        if self.overlay:
            return self.overlay.get_node(x, y)

        return None

    def __getitem__(self, x):
        return self._columns[x]

    def __str__(self):
        image = []
        for y in range(self.height):
            line = []
            for x in range(self.width):
                node = self[x][y]
                onode = self.get_overlay_node(x, y)
                if onode and onode.color:
                    color = add_color(node.color, onode.color)
                    tc = self.term.color_rgb(*color)
                    line.append(tc + str(node))
                    # line.append(node.cadd(onode).colored)
                else:
                    line.append(node.colored)

            image.append("".join(line))

        return "\n".join(image)


SCREEN = Screen(20, 20)


def get_colors(palette="default"):
    return PALETTE[palette]


def get_status_message():
    return getpass.getuser() + "@" + platform.node()


def status(term, colors, message):
    left_txt = message
    now = datetime.datetime.now().time()
    right_txt = now.strftime("%H:%M:%S")

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


def resize_handler(term):
    def on_resize(*_):
        print(term.clear)
        SCREEN.configure(term.width, term.height - 1)
    return on_resize


def main():
    term = Terminal()
    colors = get_colors()
    config = Configuration()  # TODO
    config["colors"] = colors
    config["overlay"] = OVERLAY
    SCREEN.configure(term.width, term.height - 1, term, config)
    key = None
    status_message = get_status_message()

    signal.signal(signal.SIGWINCH, resize_handler(term))

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        try:
            while key is None or key.code != term.KEY_ESCAPE:
                if SCREEN.step():
                    print(term.move_xy(0, 0) + str(SCREEN), end="")
                status(term, colors, status_message)
                key = term.inkey(timeout=UPDATE_TIME, esc_delay=UPDATE_TIME / 10)
                time.sleep(UPDATE_TIME)
        except KeyboardInterrupt:
            pass
