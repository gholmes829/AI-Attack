"""
Author: Grant Holmes
Contact: g.holmes429@gmail.com
Date: 08/16/2020

Runs main in either normal or testing mode
"""

import sys
from game import Game
from testing.timing import timeFunc

testing = False


def main():
    game = Game()

    if testing:
        timeFunc(game.run)
    else:
        game.run()


if __name__ == "__main__":
    main()
    sys.exit()
