"""
Author: Grant Holmes
Contact: g.holmes429@gmail.com
Date: 08/16/2020

Program driver, called from __main__

Classes:
    Game
"""

from core.engine import GameEngine
from core.state import GameState
from data import settings
from data.assets import colors


class Game:
    """
    Main driver for this game. Creates necessary game windows in __init__. Handles flow of updating and running events.
    """
    engine = GameEngine()
    game = GameState()

    def __init__(self):
        self.engine.makeBackground(settings.mapSize, colors["lightBlue"], makeGrid=True, color2=colors["white"])
        self.engine.makeWindow(settings.sidePanel, (settings.mapSize[0], 0), colors["purple"])

    def run(self):
        """Drives game"""
        while self.engine.keepRunning():
            self.engine.clearScreen()

            self.game.runEvent(self.engine.dt)

            self.engine.updateScreen(self.game.getSprites(), self.game.getText())
