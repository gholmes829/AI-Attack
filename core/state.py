"""
Author: Grant Holmes
Contact: g.holmes429@gmail.com
Date: 08/16/2020

Manages game logic and game event handling. Has full control over sprites and all other action.

Classes:
    GameState
    EnemySearchQueue
"""

from core import sprites
from data.peripherals import getMouse
from core.board import Map, Coord
from data import settings

from time import time
from queue import PriorityQueue
from random import randint, choice


class GameState:
    """Manages game logic"""

    def __init__(self):
        # main components
        self.map = Map()
        self.sprites = sprites.SpriteEngine()

        # event management -> eventName: {event: functionObject, requires dt: bool}
        self.events = {
            "spawnPlayer": {"run": self.spawnPlayer, "isTimeDependent": False},
            "build": {"run": self.buildWalls, "isTimeDependent": False},
            "generate": {"run": self.generateMap, "isTimeDependent": False},
            "spawnWave": {"run": self.spawnWave, "isTimeDependent": False},
            "update": {"run": self.update, "isTimeDependent": True},
            "gameOver": {"run": self.gameOver, "isTimeDependent": False},
            "wait": {"run": self.wait, "isTimeDependent": False},
        }

        # events
        self.prevEvent = None
        self.currEvent = "spawnPlayer"

        # walls
        self.wallsLeft = 100

        # searching
        self.toSearch = EnemySearchQueue()
        self.searchesPerFrame = 1
        self.trapped = False
        self.trappedCounter = 0
        self.trappedDelay = 60

        # player modifiers
        self.playerHealth = 10
        self.playerSpeed = 4
        self.bulletCoolDown = 15
        self.bulletCounter = 0

        # game stats
        self.score = 0

        # wave modifiers
        self.waveNum = 1
        self.timer = time()
        self.delay = 3

        # enemy modifiers
        self.enemiesPerWave = 3
        self.increasePerWave = (1, 5)
        self.enemySpeed = 2
        self.enemyHealth = 2
        self.deviation = (1, 2)

        self.maxEnemySpeed = 7
        self.maxEnemyHealth = 5

    def runEvent(self, dt):
        """executes current event and updates/ moves sprites"""

        if self.events[self.currEvent]["isTimeDependent"]:
            self.events[self.currEvent]["run"](dt)

        else:
            self.events[self.currEvent]["run"]()

        self.prevEvent = self.currEvent
        self.currEvent = self.getNext()

        self.updateSprites(dt)

    def getNext(self):
        """gets next event to be executed based upon current state"""
        if self.prevEvent == "spawnPlayer":
            # spawns player -> build walls
            return "build"

        if self.prevEvent == "build":
            if self.wallsLeft == 0:
                # no walls left to build -> generate map
                return "generate"
            else:
                # some walls left -> continue to build
                return "build"

        if self.prevEvent == "generate":
            # map generated -> wait before spawning first wave
            return "wait"

        if self.prevEvent == "spawnWave":
            # wave just spawned -> run and update sprites
            return "update"

        if self.prevEvent == "update":
            if self.sprites.getPlayer().health <= 0:
                # running and updating sprites, player is dead -> game is over
                return "gameOver"
            elif len(self.sprites.enemies) > 0:
                # running and updating sprites, wave is not complete -> continue wave
                return "update"
            else:
                # running and updating sprites, all enemies have died -> wait and set countdown before next wave
                self.waveNum += 1
                return "wait"

        if self.prevEvent == "wait":
            if time() - self.timer >= self.delay:
                # waiting for countdown, countdown is complete -> spawn wave
                return "spawnWave"
            else:
                # waiting for countdown, countdown is incomplete -> continue waiting
                return "wait"

        if self.prevEvent == "gameOver":
            # game is over -> continue displaying endgame until player exits game
            return "gameOver"

    def getSprites(self):
        """allows access to all sprites"""
        return self.sprites.all

    def getText(self):
        """generates and returns text to be blitted appropriate for current event"""
        if self.currEvent == "update" or self.currEvent == "spawnWave":
            # wave num, score, hp
            health = int(self.sprites.getPlayer().health * 100 / self.sprites.getPlayer().maxHealth)
            return [" Wave: " + str(self.waveNum) + " ", " Score: " + str(self.score) + " ",
                    None, " HP: " + str(health) + " "]

        elif self.currEvent == "build":
            # game name, walls left
            return [" AI ATTACK ", None, " " + str(self.wallsLeft) + " walls "]

        elif self.currEvent == "generate":
            # loading
            return [" Generating... "]

        elif self.currEvent == "gameOver":
            # game over, final score
            return [" GAME OVER ", " Final Score: " + str(self.score) + " "]

        elif self.currEvent == "wait":
            # wave num, score, hp, countdown
            health = int(self.sprites.getPlayer().health * 100 / self.sprites.getPlayer().maxHealth)
            return [" Wave: " + str(self.waveNum) + " ", " Score: " + str(self.score) + " ", None,
                    " HP: " + str(health) + " ", " Prepare: " + str(self.delay - int(time() - self.timer)) + " "]

        else:
            return [None]

    def updateSprites(self, dt):
        """checks for and handles collisions, then updates movements"""
        self.sprites.checkCollisions()
        self.sprites.update(dt)
        self.score = self.sprites.enemiesKilled

    def spawnPlayer(self):
        """spawns player in middle of board, users instance variable speed as parameter"""
        pos = Coord(int(settings.numCells[0] / 2), int(settings.numCells[1] / 2))
        self.sprites.spawnPlayer(pos, self.playerHealth, self.playerSpeed)

    def buildWalls(self):
        """gets mouse position and allows player to dynamically build walls if placement valid"""
        if self.wallsLeft > 0:
            mouse = getMouse()
            smallPos = Coord(mouse["mousePosition"], big=True).small()

            if mouse["leftClick"] and smallPos not in self.map.edges and \
                    smallPos != self.sprites.getPlayer().location and \
                    settings.isInCellMap(smallPos):

                if smallPos not in self.sprites.walls:
                    self.sprites.buildWall(smallPos)
                    self.wallsLeft -= 1

            elif mouse["rightClick"]:
                if smallPos in self.sprites.walls:
                    self.sprites.deleteWall(smallPos)
                    self.wallsLeft += 1

    def generateMap(self):
        """passes walls to map, generates gates and abstraction levels for HPA* pathfinding"""
        self.map.generate(self.sprites.walls.keys())

    def wait(self):
        """counts down before starting wave and spawning enemies"""
        if (time() - self.timer >= self.delay and self.prevEvent == "update") or self.prevEvent == "generate":
            self.timer = time()

    def spawnWave(self):
        """spawns enemies on edge of map, randomly modifies parameters within constraints, updates modifiers"""

        edges = self.map.edges.copy()

        for i in range(self.enemiesPerWave):
            # randomizes and applies modifiers
            speed = self.enemySpeed
            health = self.enemyHealth

            randomDev = randint(-self.deviation[0], self.deviation[1])
            speed += randomDev/2

            randomDev = randint(-self.deviation[0], self.deviation[1])
            health += randomDev

            start = choice(edges)
            edges.remove(start)

            self.sprites.spawnEnemy(start, health, speed)

        # increases difficulty for next wave

        numNewEnemies = randint(self.increasePerWave[0], self.increasePerWave[1])

        ds = randint(0, 10) / 20
        healthIncrease = randint(0, 1)

        if self.enemiesPerWave + numNewEnemies < len(self.map.edges):
            self.enemiesPerWave += numNewEnemies
        else:
            self.enemiesPerWave += (len(self.map.edges) - self.enemiesPerWave)

        if self.enemySpeed + ds < self.maxEnemySpeed:
            self.enemySpeed += ds

        if self.enemyHealth + healthIncrease < self.maxEnemyHealth:
            self.enemyHealth += healthIncrease

    def update(self, dt):
        """updates map w/ current walls, shoots bullets, manages conditional pathfinding"""

        if len(self.sprites.destroyedWalls) > 0:
            wall = self.sprites.destroyedWalls.pop(0)
            self.map.update(wall)

        mouseState = getMouse()
        if mouseState["leftClick"] and int(self.bulletCounter) <= 0:
            self.shoot(mouseState["mousePosition"])
            self.bulletCounter = self.bulletCoolDown

        elif self.bulletCounter > 0:
            self.bulletCounter -= 1*dt

        for enemy in self.sprites.enemies:
            if self.shouldSearch(enemy):
                enemy.queued = True

                # add to priority queue with distance from player as priority
                self.toSearch.putEnemy(enemy.distToPlayer, enemy)

        self.updateTrapped(dt)

        if not self.trapped:
            for i in range(self.searchesPerFrame):
                if not self.toSearch.empty():
                    enemy = self.toSearch.getEnemy()

                    if enemy.fixed:
                        # if enemy is in close proximity with player
                        if enemy.distToPlayer <= 7.5:
                            self.setClosePath(enemy)

                        else:
                            # if enemy is on gate
                            if enemy.location in self.map.gateCoords:
                                self.setGatedPath(enemy)

                            # else if enemy is not on gate
                            else:
                                self.setOffroadPath(enemy)

                        if self.trapped:
                            self.trappedCounter = self.trappedDelay

    def shoot(self, pos):
        """player tries to shoot bullet towards mouse"""

        playerPos = Coord(self.sprites.getPlayer().rect.center[0],
                          self.sprites.getPlayer().rect.center[1], big=True)

        target = Coord(pos[0], pos[1], big=True)

        self.sprites.spawnBullet(playerPos, target)

    def shouldSearch(self, enemy):
        """enemy should search if it is queued and (path is empty or path is now inaccurate) or is on gate"""
        if not enemy.queued and enemy.shouldSearch() and \
                (enemy.location in self.map.gateCoords or enemy.path is None or len(enemy.path) == 0):
            return True
        else:
            return False

    def updateTrapped(self, dt):
        """manages how often enemies should try to pathfind when player is inaccessible to improve performance"""
        if self.trapped:
            if int(self.trappedCounter) <= 0:
                playerPos = self.sprites.getPlayer().location
                numEnemies = len(self.sprites.enemies)
                randEnemyPos = self.sprites.enemies.sprites()[randint(0, numEnemies-1)].location

                # enemies are no longer trapped if path can be found from player to random enemy
                if not self.map.search(playerPos, randEnemyPos, "A*").failed:
                    self.trapped = False
                else:
                    self.trappedCounter = self.trappedDelay
            else:
                self.trappedCounter -= 1 * dt

    def setClosePath(self, enemy):
        """sets enemy's path when enemy is close to player, use A* for improved accuracy"""
        path = self.map.search(enemy.location, self.sprites.getPlayer().location, "A*",
                               sprites.Enemy.pathMap)
        enemy.setPath(path)
        if path.trapped:
            self.trapped = True

    def setGatedPath(self, enemy):
        """sets enemy's path when enemy is far from player and on gate, uses HPA* for improved performance"""
        targetGate = self.map.getRandomGate(self.sprites.getPlayer().location)
        playerGates = self.map.getGates(self.sprites.getPlayer().location)
        enemyPaths = sprites.Enemy.pathMap

        if targetGate is not None:
            path = self.map.search(enemy.location, targetGate, "HPA*", paths=enemyPaths, altTargets=playerGates)
            enemy.setPath(path)
            if path.trapped:
                self.trapped = True

    def setOffroadPath(self, enemy):
        """sets enemy's path when enemy is far from player and not on gate, used A* to get to gate then HPA*"""
        homeGate = self.map.getClosestGate(enemy.location, self.sprites.getPlayer().location)
        enemyGates = self.map.getGates(enemy.location)

        targetGate = self.map.getRandomGate(self.sprites.getPlayer().location)
        playerGates = self.map.getGates(self.sprites.getPlayer().location)

        enemyPaths = sprites.Enemy.pathMap

        if targetGate is not None and homeGate is not None:
            path = self.map.search(enemy.location, homeGate, "A*", altTargets=enemyGates)
            if not path.failed:
                path2 = self.map.search(path.end, targetGate, "HPA*", paths=enemyPaths, altTargets=playerGates)
                path.extend(path2)
            enemy.setPath(path)

            if path.trapped:
                self.trapped = True

    def gameOver(self):
        """player is dead, removes all sprites except for walls"""
        for sprite in self.sprites.all:
            if sprite.name != "wall":
                sprite.kill()


class EnemySearchQueue(PriorityQueue):
    """extension of priority queue to handle managing enemies and when they pathfind"""

    def __init__(self):
        PriorityQueue.__init__(self)
        self.tieBreakers = set()

    def getEnemy(self):
        """pops from queue until finding enemy that is fixed, re-adding enemies that weren't ready"""
        reFeed = []
        item = self.get()
        enemy = item[2]
        self.tieBreakers.remove(item[1])
        while not enemy.fixed:
            reFeed.append(item)
            if not self.empty():
                item = self.get()
                enemy = item[2]
                self.tieBreakers.remove(item[1])
            else:
                break
        while len(reFeed) != 0:
            entry = reFeed.pop(0)
            self.putEnemy(entry[0], entry[2])
        return enemy

    def putEnemy(self, priority, enemy):
        """puts enemy in queue with priority, adds tiebreaker to ensure entries are unique and won't throw exceptions"""
        tieBreaker = 0
        while tieBreaker in self.tieBreakers:
            tieBreaker += 1
        self.put((priority, tieBreaker, enemy))
        self.tieBreakers.add(tieBreaker)
