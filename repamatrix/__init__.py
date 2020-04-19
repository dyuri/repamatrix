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


class Configuration(dict):
    pass
    

class Node:
    
    def __init__(self, term, config):
        self.term = term
        self.config = config
        self._colors = config.get('colors', get_colors())
        self._color = term.color_rgb(*random.choice(self._colors[1:-1]))
        self._char = random.choice(config.get('charset', CHARSET["default"]))

    def __str__(self):
        return self._color + self._char


class Spawner:
    
    def __init__(self, height, term, config):
        self.height = height
        self.term = term
        self.config = config

        self.pos = 0

    def next_node(self):
        return Node(self.term, self.config)

    def step(self, column):
        column[self.pos] = self.next_node()

        self.pos += 1
        if self.pos >= self.height:
            return None

        return self


class Column:

    def __init__(self, height, term, config):
        self.height = height
        self.term = term
        self.config = config

        self._nodes = []
        self._clear()
        self._spawner = None

    def _clear(self):
        self._nodes = [" " for _ in range(self.height)]

    def __getitem__(self, y):
        return self._nodes[y]

    def __setitem__(self, y, node):
        self._nodes[y] = node

    def spawn(self, probability=None):
        if probability is None:
            probability = self.config.get('spawn_probability', .01)

        if random.random() < probability:
            return Spawner(self.height, self.term, self.config)
        else:
            return None

    def step(self):
        if self._spawner:
            self._spawner = self._spawner.step(self)
        else:
            self._spawner = self.spawn()


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
        self._columns = self._init_columns()

    def _init_columns(self):
        return [Column(self.height, self.term, self.config) for _ in range(self.width)]

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

    def __getitem__(self, x):
        return self._columns[x]

    def __str__(self):
        return '\n'.join([''.join([str(node) for node in line]) for line in self.lines])


SCREEN = Screen(20, 20)


def get_colors(palette="default"):
    return PALETTE[palette]


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
    SCREEN.configure(term.width, term.height - 1, term, config)
    key = None

    signal.signal(signal.SIGWINCH, resize_handler(term))

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        try:
            while key is None or key.code != term.KEY_ESCAPE:
                if SCREEN.step():
                    print(term.move_xy(0, 0) + str(SCREEN), end="")
                status(term, colors, "hello bello")
                key = term.inkey(timeout=UPDATE_TIME, esc_delay=UPDATE_TIME / 10)
                time.sleep(UPDATE_TIME)
        except KeyboardInterrupt:
            pass
