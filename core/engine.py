"""
Author: Grant Holmes
Contact: g.holmes429@gmail.com
Date: 08/16/2020

Handles and manages basic GUI and blitting to screen. Also initializes pygame and maintains frame rate/ allows for
frame rate independence through dt.

Classes:
    GameEngine
"""

import pygame
from data.assets import colors
from data import settings


class GameEngine:
    """
    Handles GUI and frame rate
    """
    clock = pygame.time.Clock()
    running = True

    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode(settings.screenSize)
        self.background = None

        self.font = pygame.font.SysFont("impact", 28)
        self.smallFont = pygame.font.SysFont("impact", 20)

        self.dt = None

        self.windows = {}
        pygame.display.set_caption(settings.gameName)

    def handleEvents(self):
        """Checks to see if X is clicked"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                pygame.quit()

    def keepRunning(self):
        """Checks to see if game should still run, updates frame rate"""
        self.handleEvents()

        # dt is milliseconds passed between frames
        self.dt = self.clock.tick(settings.targetFrameRate) / 1000 * settings.normalizedFrameRate

        return self.running

    def clearScreen(self):
        """clears and resets game windows"""
        self.screen.blit(self.background, (0, 0))
        for window in self.windows:
            self.screen.blit(window, self.windows[window])

    def writeText(self, output):
        """blits given string text to screen. Uses instance variable font. Output should be iterable"""
        offset = 0
        for string in output:
            if string is not None:
                text = self.font.render(string, True, colors["black"], colors["lightBlue"])
                textRect = text.get_rect()
                textRect.center = (
                    settings.mapSize[0] + int(settings.sidePanel[0] / 2), int(settings.mapSize[1] / 10) + offset)
                self.screen.blit(text, textRect)
            offset += 50

    def displayFPS(self):
        """displays current frames per second on screen, marker of performance"""
        fps = int(self.clock.get_fps())
        output = " FPS: " + str(fps) + " "
        text = self.smallFont.render(output, True, colors["black"], colors["lightBlue"])
        textRect = text.get_rect()
        textRect.center = (
            settings.mapSize[0] + int(settings.sidePanel[0] / 2), int(settings.mapSize[1] - settings.mapSize[1] / 10))
        self.screen.blit(text, textRect)

    def updateScreen(self, sprites, text):
        """draws updated sprites, writes texts, and sends data to screen"""
        sprites.draw(self.screen)

        self.writeText(text)

        self.displayFPS()

        pygame.display.flip()

    def makeBackground(self, size, color, makeGrid=False, color2=None):
        """makes main game window, can either make solid color or grid"""
        self.background = pygame.Surface(size)

        if not makeGrid:
            self.background.fill(color)
        else:
            for x in range(settings.numCells[0]):
                alt = x % 2
                for y in range(settings.numCells[1] + 1):
                    rect = pygame.Surface(settings.gridSize)

                    if y % 2 == 1 and alt == 0:
                        rect.fill(color)
                        self.background.blit(rect, (y * settings.gridSize[0], x * settings.gridSize[1]))

                    elif y % 2 == 1 and alt == 1:
                        rect.fill(color)
                        self.background.blit(rect, (y * settings.gridSize[0] - settings.gridSize[0],
                                                    x * settings.gridSize[1]))

                    elif y % 2 == 0 and alt == 0:
                        rect.fill(color2)
                        self.background.blit(rect, (y * settings.gridSize[0], x * settings.gridSize[1]))

                    elif y % 2 == 0 and alt == 1:

                        rect.fill(color2)
                        self.background.blit(rect, (y * settings.gridSize[0] + settings.gridSize[0],
                                                    x * settings.gridSize[1]))

                    # makes border where enemies spawn
                    if y == 0 or y == settings.numCells[1]-1 or x == 0 or x == settings.numCells[0]-1:
                        rect.fill(color)
                        self.background.blit(rect, (y * settings.gridSize[0], x * settings.gridSize[1]))

    def makeWindow(self, size, pos, color):
        """makes any auxiliary game windows, solid color"""
        window = pygame.Surface(size)
        window.fill(color)
        self.windows[window] = pos
        self.screen.blit(window, pos)
