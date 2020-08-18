"""
Author: Grant Holmes
Contact: g.holmes429@gmail.com
Date: 08/16/2020

Manages creating, handling, updating, and deleting sprites through SpriteEngine. Sprite classes derived from
pygame.sprite.Sprite. Sprite and MovingSprite classes are derived from this to make base classes for actually sprites
seen in game.

Classes:
    SpriteEngine
    Sprite
    MovingSprite
    Player
    Enemy
    Bullet
    Wall

"""

from data.peripherals import getKey
from core.board import CoordMap, Coord
from data.assets import colors
from data import settings

import pygame.sprite
from pygame import Surface, Rect
import math


class SpriteEngine:
    """manages spawning and storing all sprites"""

    def __init__(self):
        self.all = pygame.sprite.Group()

        self.enemies = pygame.sprite.Group()
        self.player = pygame.sprite.GroupSingle()
        self.bullets = pygame.sprite.Group()

        self.walls = {}
        self.destroyedWalls = []
        self.wallCount = 0

        self.enemiesKilled = 0

    def update(self, dt):
        """updates each enemies dist away from player to optimize search priority then calls each sprites update func"""

        for enemy in self.enemies:
            dx = self.player.sprite.location.x - enemy.location.x
            dy = self.player.sprite.location.y - enemy.location.y
            enemy.distToPlayer = math.sqrt(dx ** 2 + dy ** 2)

            if enemy.path is not None and enemy.path.end is not None:
                dx = self.player.sprite.location.x - enemy.path.end.x
                dy = self.player.sprite.location.y - enemy.path.end.y
                enemy.pathError = math.sqrt(dx ** 2 + dy ** 2)

        self.all.update(dt, self.walls.keys())

    def checkCollisions(self):
        """checks for and handles collisions bt player, enemies, bullets, and walls"""
        self.destroyedWalls.clear()

        if len(pygame.sprite.groupcollide(self.enemies, self.player, True, False)) > 0:
            self.getPlayer().health -= 1

        enemiesHit = pygame.sprite.groupcollide(self.enemies, self.bullets, False, True)
        for enemy in enemiesHit.keys():
            enemy.getHit()
            if len(enemy.groups()) <= 0:
                self.enemiesKilled += 1

        wallsHit = pygame.sprite.groupcollide(self.walls.values(), self.bullets, False, True)
        for wall, bullet in wallsHit.items():
            wall.getHit()

            if wall.health <= 0:
                self.destroyedWalls.append(wall.location)
                self.deleteWall(wall.location)

    def getPlayer(self):
        """returns player sprite"""
        return self.player.sprite

    def buildWall(self, coord):
        """creates wall and adds it to wall dict with coord pos as key"""
        wall = Wall(coord)
        self.all.add(wall)
        self.walls[coord] = wall
        self.wallCount += 1

    def deleteWall(self, coord):
        """destroys and deletes wall and removes it from wall dict"""
        self.walls[coord].kill()
        del self.walls[coord]
        self.wallCount -= 1

    def spawnPlayer(self, coord, health, speed):
        """spawns player and adds to groups"""
        player = Player(coord, health, speed)
        self.all.add(player)
        self.player.add(player)

    def spawnEnemy(self, coord, health, speed):
        """spawns enemy and adds to groups"""
        enemy = Enemy(coord, health, speed)
        self.all.add(enemy)
        self.enemies.add(enemy)

    def spawnBullet(self, origin, target):
        """spawns bullet and adds to groups"""
        bullet = Bullet(origin, target)
        self.all.add(bullet)
        self.bullets.add(bullet)


class Sprite(pygame.sprite.Sprite):
    """basic extension that includes basic information, used as base class for sprite derivatives"""

    def __init__(self, name, coord):
        pygame.sprite.Sprite.__init__(self)
        self.name = name
        self.location = coord

        self.image = Surface(settings.gridSize)
        self.rect = self.image.get_rect()

        self.pos = coord.big()

        self.rect.x = self.pos.x
        self.rect.y = self.pos.y


class MovingSprite(Sprite):
    """extension of sprite that provides basic for tile based movement"""

    def __init__(self, name, coord, speed):
        Sprite.__init__(self, name, coord)
        self.speed = speed
        self.velocity = [0, 0]

        self.prevLocation = None
        self.target = None
        self.fixed = True

    @staticmethod
    def speedDecay(speed):
        """function incorporating exponential decay for px/frame movement calculation, 1 <= speed <= 15"""
        a = 1.441
        b = -0.1
        c = -0.304
        return a * speed * (math.e ** (b * speed)) + c

    def move(self, dt):
        """allows sprites to move between tiles, speed dictates how many steps between tiles"""
        dx = self.velocity[0] * self.speedDecay(self.speed) * dt
        dy = self.velocity[1] * self.speedDecay(self.speed) * dt

        if self.velocity[0] != 0 and abs(self.target.x * settings.gridSize[0] - self.rect.x) < abs(dx):
            dx = self.target.x * settings.gridSize[0] - self.rect.x

        if self.velocity[1] != 0 and abs(self.target.y * settings.gridSize[1] - self.rect.y) < abs(dy):
            dy = self.target.y * settings.gridSize[1] - self.rect.y

        self.pos.x += dx
        self.pos.y += dy

        self.rect.x = self.pos.x
        self.rect.y = self.pos.y

        if self.rect.x == self.target.x * settings.gridSize[0] and self.rect.y == self.target.y * settings.gridSize[1]:
            self.fixed = True
            self.velocity = [0, 0]

            self.prevLocation = self.location
            self.location = self.target


class Player(MovingSprite):
    """player that the user controls"""

    def __init__(self, coord, health, speed):
        MovingSprite.__init__(self, "player", coord, speed)
        self.image.fill(colors["blue"])

        self.maxHealth = 5
        self.health = health

    def update(self, dt, walls):
        """takes in input from keyboard to determine movement"""
        if self.fixed:
            if self.target is not None:
                self.location = self.target

            if getKey("up"):
                self.velocity[1] -= 1

            if getKey("right"):
                self.velocity[0] += 1

            if getKey("down"):
                self.velocity[1] += 1

            if getKey("left"):
                self.velocity[0] -= 1

            if self.velocity != [0, 0]:
                # check that potential move is not in walls and is still in map
                if self.location + self.velocity in walls or not settings.isInCellMap(self.location + self.velocity):
                    if (self.location + [self.velocity[0], 0] in walls and
                        self.location + [0, self.velocity[1]] in walls) or (not settings.isInCellMap(
                            self.location + [self.velocity[0], 0]) and not settings.isInCellMap(
                                self.location + [0, self.velocity[1]])):

                        self.velocity = [0, 0]

                    elif self.location + [self.velocity[0], 0] in walls or not settings.isInCellMap(
                            self.location + [self.velocity[0], 0]):
                        self.velocity = [0, self.velocity[1]]
                    else:
                        self.velocity = [self.velocity[0], 0]

                elif self.velocity[0] != 0 and self.velocity[1] != 0:
                    if self.location + [self.velocity[0], 0] in walls and \
                            self.location + [0, self.velocity[1]] in walls:
                        self.velocity = [0, 0]

            self.target = self.location + self.velocity

        if self.velocity != [0, 0]:
            self.fixed = False
            self.move(dt)


class Enemy(MovingSprite):
    """enemy sprite, searches for and follows player, attempting to collide"""
    pathMap = CoordMap()
    locations = set()

    def __init__(self, coord, health, speed):
        MovingSprite.__init__(self, "enemy", coord, speed)

        self.originalColor = [0, 255, 25]
        self.color = self.originalColor

        self.image.fill(self.originalColor)

        self.maxHealth = health
        self.health = health

        # necessary for searching:
        self.path = None
        self.queued = False
        self.distToPlayer = None
        self.pathError = 0

        Enemy.locations.add(self.location)

    def update(self, dt, walls):
        """sets new tile to move to if enemy is currently fixed on tile"""
        if self.fixed:
            if self.path is not None and len(self.path) > 0:
                self.target = self.path.get()
                Enemy.locations.add(self.target)

                if self.location in Enemy.locations:
                    Enemy.locations.remove(self.location)

                Enemy.pathMap[self.target] = False
                self.velocity = [self.target.x - self.location.x, self.target.y - self.location.y]

        if self.velocity != [0, 0]:
            self.fixed = False
            self.move(dt)

    def destroy(self):
        """deletes enemy and removes path from enemy map"""
        if self.target in Enemy.locations:
            Enemy.locations.remove(self.target)
        if self.path is not None:
            for pt in self.path:
                if pt in Enemy.pathMap:
                    Enemy.pathMap[pt] = False
        self.kill()

    def shouldSearch(self):
        """determines whether enemy should get a new path"""
        if self.fixed and \
                ((self.path is None or len(self.path) == 0) or self.pathError > 10):
            return True
        else:
            return False

    def getHit(self):
        """handles what happens when enemy is hit"""
        self.health -= 1
        if self.health <= 0:
            self.destroy()
            return

        # change color when hit
        self.color[1] -= int(self.originalColor[1] / (self.maxHealth - 1))
        self.color[0] += int(255 / (self.maxHealth - 1))
        self.image.fill(self.color)

        if self.health == 1:
            self.image.fill(colors["red"])

        # lower speed when hit
        if self.speed - 1 > 1:
            self.speed -= 1

    def setPath(self, path):
        """sets new path for enemy to follow"""
        self.target = None

        if self.path is not None:
            for pt in self.path:
                Enemy.pathMap[pt] = False

        self.path = path
        if len(self.path) > 0:
            self.path.get()

        self.queued = False

        for pt in path:
            Enemy.pathMap[pt] = True

    def __lt__(self, other):
        """defined if stored in priority queue and primary cost results in tie"""
        if type(other) == Enemy:
            return self.distToPlayer < other.distToEnd
        else:
            raise TypeError("Can't compare enemy with type: " + str(type(other)))


class Bullet(pygame.sprite.Sprite):
    """bullet that player can shoot"""

    def __init__(self, origin, target):
        pygame.sprite.Sprite.__init__(self)

        self.name = "bullet"

        self.image = Surface(settings.gridSize)
        self.rect = Rect((0, 0), (int(settings.gridSize[0]/2), int(settings.gridSize[1]/2)))

        self.image.fill(colors["white"])
        self.image.set_colorkey(colors["white"])

        width = int(settings.gridSize[0] / 2)
        height = int(settings.gridSize[0] / 2)
        radius = int(settings.gridSize[0] / 2)

        pygame.draw.circle(self.image, colors["orange"], (width, height), radius)

        rawDirection = [target.x - origin.x, target.y - origin.y]
        magnitude = math.sqrt(rawDirection[0] ** 2 + rawDirection[1] ** 2)
        self.direction = [rawDirection[0] / magnitude, rawDirection[1] / magnitude]

        self.pos = origin
        self.pos.x += self.direction[0] * 10
        self.pos.y += self.direction[1] * 10

        self.rect.x = self.pos.x
        self.rect.y = self.pos.y

        self.speed = 15

    def update(self, dt, walls):
        """updates position of bullet, destroys if off map"""
        dx = self.direction[0] * self.speed * dt
        dy = self.direction[1] * self.speed * dt

        # normalize movement so bullet never skips more than one cell
        if abs(dx) > settings.gridSize[0] and abs(dx) > abs(dy):
            temp = settings.gridSize[0] * int((dx / abs(dx)))
            dy = dy * temp / dx
            dx = temp

        elif abs(dy) > settings.gridSize[1]:
            temp = settings.gridSize[1] * int((dy / abs(dy)))
            dx = dx * temp / dy
            dy = temp

        self.pos.x += dx
        self.pos.y += dy

        self.rect.center = [self.pos.x, self.pos.y]

        if not settings.isInCellMap(self.pos.small()):
            self.destroy()

    def destroy(self):
        self.kill()


class Wall(Sprite):
    """wall that prevents movement"""

    def __init__(self, coord):
        Sprite.__init__(self, "wall", coord)

        self.originalColor = colors["black"]
        self.color = list(self.originalColor)

        self.image.fill(self.originalColor)

        self.originalCircleColor = colors["purple"]
        self.circleColor = list(self.originalCircleColor)

        self.width = int(settings.gridSize[0] / 2)
        self.height = int(settings.gridSize[1] / 2)
        self.radius = int(settings.gridSize[0] / 4)

        pygame.draw.circle(self.image, self.originalCircleColor, (self.width, self.height), self.radius)

        self.maxHealth = 4
        self.health = self.maxHealth

    def update(self, dt, walls):
        """dummy function"""
        pass

    def getHit(self):
        """effects of wall being hit by bullet, changes color"""
        self.health -= 1

        if self.health > 0:
            # change color when hit

            self.color[0] += int(255 / (self.maxHealth - 0.5))
            self.color[1] += int(255 / (self.maxHealth - 0))
            self.color[2] += int(255 / (self.maxHealth - 0.75))

            self.circleColor[0] -= int(self.originalCircleColor[0] / (self.maxHealth - 1))
            self.circleColor[1] -= int(self.originalCircleColor[1] / (self.maxHealth - 1))
            self.circleColor[2] -= int(self.originalCircleColor[2] / (self.maxHealth - 1))

            self.image.fill(self.color)
            pygame.draw.circle(self.image, self.circleColor, (self.width, self.height), self.radius)
