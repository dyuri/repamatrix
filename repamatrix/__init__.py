from blessed import Terminal
import datetime
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

NODES = {
    0: []
}


class Node:

    def __init__(self, column=0, speed=SPEED, white=None, charset=CHARSET["default"], colors=PALETTE["default"]):
        self.type = "node"
        self.x = column
        self.y = 0
        self.white = white if white is not None else random.choice([True, False])
        self.last_char = None
        self.last_step = 0
        self.speed = speed
        self.charset = charset
        self.colors = colors

    @property
    def next_char(self):
        char = random.choice(self.charset)
        self.last_char = char

        return char

    def random_color(self):
        return random.choice(self.colors[1:-1])  # omit black and white

    def need_step(self, time):
        return self.last_step + self.speed < time

    def step(self, term, now):
        self.last_step = now
        if self.y > term.height - (1 if self.white else 2):
            return False
        if self.white:
            movement = ""
            if self.last_char:
                movement += term.move_xy(self.x, self.y - 1) + term.color_rgb(*self.random_color()) + self.last_char
            if self.y < term.height - 1:
                movement += term.move_xy(self.x, self.y) + term.color_rgb(*self.colors[-1]) + self.next_char
        else:
            movement = term.move_xy(self.x, self.y) + term.color_rgb(*self.random_color()) + self.next_char

        self.y += 1
        return movement


class Eraser(Node):

    def __init__(self, column=0, speed=SPEED):
        super().__init__(column, speed, False, " ")

        self.type = "eraser"
        self.last_char = " "

    @property
    def next_char(self):
        return " "

    def random_color(self):
        return self.colors[0]


# TODO
NODES[0].append(Node())


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


def step(term, colors, nodes):
    now = datetime.datetime.now().timestamp()
    for column, cnodes in nodes.items():
        print(term.move_x(column), end="")
        for node in cnodes:
            if node.need_step(now):
                # TODO
                movement = node.step(term, now)
                if movement:
                    print(movement, end="")
                else:
                    if node.type == "node":
                        cnodes.append(Eraser())
                    else:
                        cnodes.append(Node())
                    cnodes.remove(node)


def resize_handler(term):
    def on_resize(*_):
        print(term.clear)
    return on_resize


def main():
    term = Terminal()
    colors = get_colors()
    key = None

    signal.signal(signal.SIGWINCH, resize_handler(term))

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        try:
            while key is None or key.code != term.KEY_ESCAPE:
                step(term, colors, NODES)
                status(term, colors, "hello bello")
                key = term.inkey(timeout=UPDATE_TIME, esc_delay=UPDATE_TIME / 10)
        except KeyboardInterrupt:
            pass
