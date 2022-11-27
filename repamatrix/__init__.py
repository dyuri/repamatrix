import platform
import getpass
from .matrix import Configuration, get_colors, matrix

SPEED = .1

OVERLAY = [
    "     DDDDD                                  III ",
    "    ..DDD                                  ...  ",
    "  DDDDDDD  YYYYY YYYY UUUUU UUUU RRRRRRRR  IIII ",
    " DDD..DDD ..YYY .YYY ..UUU .UUU ..RRR..RRR..III ",
    ".DDD .DDD  .YYY .YYY  .UUU .UUU  .RRR ...  .III ",
    ".DDD .DDD  .YYY .YYY  .UUU .UUU  .RRR      .III ",
    "..DDDDDDDD ..YYYYYYY  ..UUUUUUUU RRRRR     IIIII",
    " ........   .....YYY   ........ .....     ..... ",
    "            YYY .YYY                            ",
    "           ..YYYYYY                             ",
    "            ......                              ",
]
CMAP = {
    ".": (32, 32, 64),
    "D": (64, 64, 128),
    "Y": (64, 64, 128),
    "U": (64, 64, 128),
    "R": (64, 64, 128),
    "I": (64, 64, 128),
}


def get_user_hostname():
    return getpass.getuser() + "@" + platform.node()


def main():
    config = Configuration()  # TODO
    config["colors"] = get_colors("green")

    # TOOD
    config["overlay_image"] = "etc/punisher.jpg"
    # config["overlay_text"] = OVERLAY

    config["status_message"] = get_user_hostname()
    config["speed"] = SPEED

    matrix(config)
