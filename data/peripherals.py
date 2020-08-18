"""
Author: Grant Holmes
Contact: g.holmes429@gmail.com
Date: 08/16/2020

Allows access to keyboard, mouse, and any other peripherals
"""

import pygame

keys = {
    "up": False,
    "right": False,
    "down": False,
    "left": False,

    "space": False
}


def getLeftClick():
    return pygame.mouse.get_pressed()[0]


def getRightClick():
    return pygame.mouse.get_pressed()[2]


def getMousePos():
    return pygame.mouse.get_pos()


def getKey(key):
    keys["up"] = pygame.key.get_pressed()[pygame.K_w]
    keys["right"] = pygame.key.get_pressed()[pygame.K_d]
    keys["down"] = pygame.key.get_pressed()[pygame.K_s]
    keys["left"] = pygame.key.get_pressed()[pygame.K_a]
    keys["space"] = pygame.key.get_pressed()[pygame.K_SPACE]

    if key in keys:
        return keys[key]
    else:
        raise ValueError("Peripheral key not available...")


def getMouse():
    return {"leftClick": getLeftClick(), "rightClick": getRightClick(), "mousePosition": getMousePos()}
