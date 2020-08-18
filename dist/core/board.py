"""
Author: Grant Holmes
Contact: g.holmes429@gmail.com
Date: 08/16/2020

Generates and manages tile-based map for game. Also includes coordinate system. Map is dynamically broken into chunks
to prepare map for HPA* pathfinding. Upon generating, map pre-computes paths between chunks using regular gates. Map can
update when walls are destroyed.

Also provides a few auxiliary classes used by other modules. Paths are used by enemies in sprite class and CoordMap is
used to keep track of sprites paths in relation to another.

Classes:
    Map
    NodeGroup
    Node
    NodeSide
    Cell
    Coord
    Path
    CoordMap
"""

from data import settings

from random import randint
from queue import PriorityQueue
from itertools import combinations


class Map:
    """final map product, uses other classes to build, provides pathfinding functionality and search function"""

    def __init__(self):
        self.walls = None  # later updated through setter

        self.cells = {}
        self.paths = {}
        self.edges = []

        self.gates = set()
        self.gateCoords = set()
        self.nodes = NodeGroup(settings.numNodes, settings.cellsInNode)

        # denoting edges of map
        for pt in range(settings.numCells[0]):
            self.edges.append(Coord(pt, 0))
            self.edges.append(Coord(pt, settings.numCells[1] - 1))

        for pt in range(settings.numCells[1]):
            if pt != 0 and pt != settings.numCells[1] - 1:
                self.edges.append(Coord(0, pt))
                self.edges.append(Coord(settings.numCells[0] - 1, pt))

        # referencing cells in nodes to general dict for easy access
        for node in self.nodes:
            for cell in node.cells.values():
                self.cells[cell.location] = Reference(cell)

        # adding next-door neighbors to cells
        for node in self.nodes:
            for cell in node.cells.values():
                for side in cell.sides:
                    if settings.isInCellMap(cell.location + side):
                        cell.neighbors["A*"].add(self.cells[cell.location + side].new())
                        cell.numNeighbors += 1

    def generate(self, walls):
        """makes 'gates' throughout map dependent upon walls; precomputes paths between gates for HPA* searches"""
        self.walls = walls
        self.makeGates(self.walls)
        self.connectNodes()
        self.connectGates()
        self.makeCombos()
        self.makePaths()

    def makeGates(self, walls):
        """has each node in NodeGroup place gates on edges"""
        for node in self.nodes:
            node.placeGates(walls)

    def connectNodes(self):
        """has each node in NodeGroup get gates from adjacent neighbors on top and left sides"""
        for node in self.nodes:
            node.connectNode()

    def connectGates(self):
        """adds all gates to gates and gateCoords, makes neighbors for gates"""
        for node in self.nodes.nodes.values():
            for side in node.sides.values():
                for gate in side.gates:
                    self.gates.add(gate.new())
                    self.gateCoords.add(gate.get().location)
                    # for each gate in original node
                    for adjacent in node.gates:
                        if gate.get().location != adjacent.get().location:
                            gate.get().neighbors["allHPA*"].add(adjacent.new())
                            if adjacent in self.gates:
                                adjacent.gateNeighbors.add(gate.new())

                    # for each gate in specified neighboring node
                    if settings.isInNodeMap(node.location + side.border):
                        for neighborGate in self.nodes(node.location + side.border).gates:
                            if gate.get().location != neighborGate.get().location:
                                gate.get().neighbors["allHPA*"].add(neighborGate.new())
                                if neighborGate in self.gates:
                                    neighborGate.gateNeighbors.add(gate.new())

    def makeCombos(self):
        """has each node in NodeGroup make combinations between gates """
        for node in self.nodes:
            node.makeCombos()

    def makePaths(self):
        """pre-computes paths for all gate combinations, checks if valid"""
        for node in self.nodes:
            for combo in node.combos:
                if combo not in self.paths:
                    path = self.search(combo[0], combo[1], "A*", abort=50)
                    node.paths[combo] = path

                    if not path.failed:
                        reverseCombo = (combo[1], combo[0])
                        reversePath = Path(path[::-1])
                        node.paths[reverseCombo] = reversePath

                        self.paths[combo] = Reference(path)
                        self.paths[reverseCombo] = Reference(reversePath)

            for gate in node.gates:
                for neighborGate in gate.get().neighbors["allHPA*"]:
                    if (gate.get().location, neighborGate.get().location) in self.paths:
                        gateLocations = [cell.get().location for cell in gate.get().neighbors["HPA*"]]
                        if neighborGate.get().location not in gateLocations:
                            gate.get().neighbors["HPA*"].add(neighborGate.new())

    def update(self, wallLocation):
        """updates gates and paths when walls get destroyed"""

        nodeLocation = wallLocation.getNode()

        node = self.nodes(nodeLocation)
        wallRef = Reference(node(wallLocation))

        onSide = False
        counter = 0

        for side in node.sides.values():  # for each side
            if wallLocation in side:  # this means wall was on the edge of a node and a new gate should be placed
                # make paths in neighboring node that touches side of local node
                onSide = True

                side.addGate(wallRef.new())
                if settings.isInNodeMap(nodeLocation + side.border):
                    neighborNode = self.nodes(nodeLocation + side.border)

                    neighborNode.gates.add(wallRef.new())
                    neighborNode.sides[side.opposite].addGate(wallRef.new())

                    for gate in neighborNode.gates:

                        if gate.get().location != wallLocation:
                            gate.get().neighbors["allHPA*"].add(wallRef.new())
                            wallRef.get().neighbors["allHPA*"].add(gate.new())

                            combo = (gate.get().location, wallLocation)
                            reverse = (wallLocation, gate.get().location)

                            path = self.search(combo[0], combo[1], "A*", abort=25)

                            neighborNode.paths[combo] = path

                            if not path.failed:
                                reversePath = Path(path[::-1])
                                neighborNode.paths[reverse] = reversePath
                                self.paths[combo] = Reference(path)
                                self.paths[reverse] = Reference(reversePath)

                            neighborNode.combos.add(combo)
                            neighborNode.combos.add(reverse)

                        counter += 1

                        if counter > 2:  # limits searches for performance
                            counter = 0
                            break

                    for gate in neighborNode.gates:
                        for neighborGate in gate.get().neighbors["allHPA*"]:
                            neighbors = [cell.get().location for cell in gate.get().neighbors["HPA*"]]
                            if neighborGate.get().location not in neighbors and \
                                    (gate.get().location, neighborGate.get().location) in self.paths:
                                gate.get().neighbors["HPA*"].add(neighborGate.new())

        if onSide:  # make paths in node that side is a part of
            node.gates.add(wallRef.new())

            self.gates.add(wallRef.new())
            self.gateCoords.add(wallLocation)

            for gate in node.gates:
                if gate.get().location != wallLocation:
                    gate.get().neighbors["allHPA*"].add(wallRef.new())
                    wallRef.get().neighbors["allHPA*"].add(gate.new())

                    combo = (gate.get().location, wallLocation)
                    reverse = (wallLocation, gate.get().location)

                    path = self.search(combo[0], combo[1], "A*", abort=25)

                    node.paths[combo] = path
                    if not path.failed:
                        reversePath = Path(path[::-1])
                        node.paths[reverse] = reversePath
                        self.paths[combo] = Reference(path)
                        self.paths[reverse] = Reference(reversePath)

                    node.combos.add(combo)
                    node.combos.add(reverse)

                counter += 1

                if counter > 6:  # limits searches for performance
                    break

            for gate in node.gates:
                for neighborGate in gate.get().neighbors["allHPA*"]:
                    neighbors = [cell.get().location for cell in gate.get().neighbors["HPA*"]]
                    if neighborGate.get().location not in neighbors and \
                            (gate.get().location, neighborGate.get().location) in self.paths:
                        gate.get().neighbors["HPA*"].add(neighborGate.new())

        else:  # wall was not on a side of node; it is in the center and a new gate does not need to be made
            # for all combinations in node that resulted in a failed path, retry pathfinding
            for combo in node.combos:
                if combo not in self.paths:
                    path = self.search(combo[0], combo[1], "A*", abort=20)

                    node.paths[combo] = path
                    if not path.failed:
                        reverseCombo = (combo[1], combo[0])
                        reversePath = Path(path[::-1])
                        node.paths[reverseCombo] = reversePath

                        self.paths[combo] = Reference(path)
                        self.paths[reverseCombo] = Reference(reversePath)

            for gate in node.gates:
                for neighborGate in gate.get().neighbors["allHPA*"]:
                    neighbors = [cell.get().location for cell in gate.get().neighbors["HPA*"]]
                    if neighborGate.get().location not in neighbors and \
                            (gate.get().location, neighborGate.get().location) in self.paths:
                        gate.get().neighbors["HPA*"].add(neighborGate.new())

    def getGates(self, coord):
        """gets all gates from node that coord is a part of"""
        node = coord.getNode()
        return self.nodes(node).gates

    def getRandomGate(self, coord):
        """get a random gate from node that coord is a part of"""
        node = coord.getNode()
        if len(self.nodes(node).gates) != 0:
            c = 0
            choice = randint(0, len(self.nodes(node).gates) - 1)
            for gate in self.nodes(node).gates:
                if c == choice:
                    return gate.get().location
                c += 1
        else:
            return None

    def getClosestGate(self, coord, target):
        """get gate from node that coord is a part of that is in same node as coord closest to target"""
        node = coord.getNode()
        if len(self.nodes(node).gates) != 0:

            temp = {}

            for gate in self.nodes(node).gates:
                dx = target.x - gate.get().location.x
                dy = target.y - gate.get().location.y
                temp[gate.get().location] = dx ** 2 + dy ** 2

            return min(temp, key=temp.get)

        else:
            return None

    @staticmethod
    def h_cost(cell, target, method):
        """h_cost used for A* and HPA* to compute dist bt cell and target, select chooses method"""
        dx = abs(cell.location.x - target.x)
        dy = abs(cell.location.y - target.y)

        if method == 0:  # this method will result in a straighter line
            return dx + dy
        else:  # this method results in a more zig-zag line
            if dx > dy:
                return dx
            else:
                return dy

    def validMove(self, current, nextMove):
        """checks if going from current to nextMove is valid by checking if walls block movement"""
        if nextMove in self.walls:
            return False

        diff = nextMove - current

        if diff.x == 0 or diff.y == 0:
            return True
        elif (current + Coord(0, diff.y) in self.walls) and current + Coord(diff.x, 0) in self.walls:
            return False
        else:
            return True

    @staticmethod
    def overlaps(pt, paths):
        """tests to see if point is in paths, diversifies multi-agent pathfinding"""
        if paths is None:
            return False
        else:
            return paths[pt]

    def search(self, start, target, searchType, paths=None, abort=None, altTargets=None):
        """
        allows pathfinding through map around walls

        Parameters:
            start -> where to start search
            target -> target to pathfind to
            searchType -> A* or HPA*
            paths -> can pass in the projected paths of all enemies to reduce agent density and improve path diversity
            abort -> returns with failed path if searches this many cells, used to avoid long expensive paths
            altTargets -> if path fails to find target, checks if any in altTargets were found and returns path to them

        Search Types:
            A* -> heuristic based pathfinding with dynamic terrain costs
            HPA* -> extension of A* with levels of abstraction; map divided into chunks and HPA* searches bt chunks
        """

        counter = 0

        choice = randint(0, 4)  # allows pseudo random paths; choice used to modify cost calculation and move validity

        if choice == 4 and searchType == "HPA*":
            costMethod = 1
        else:
            costMethod = 0

        if choice < 1:
            checkOverlap = True
        else:
            checkOverlap = False

        searched = set()
        path = Path()

        targetFound = False

        frontier = PriorityQueue()  # uses priority queue rather than iterative approach to increase performance
        frontier.put((0, 0, self.cells[start].get()))

        cameFrom = {self.cells[start].get(): self.cells[start].get()}
        costSoFar = {self.cells[start].get(): 0}

        if target in self.walls or start == target:  # target can not be reached or is already reached
            path.fail()
            return path

        while not frontier.empty():
            current = frontier.get()[2]

            if current.location == target:
                targetFound = True
                break

            failed = 0

            for nextMove in [cellReference.get() for cellReference in current.neighbors[searchType]]:

                if searchType == "HPA*" and (not checkOverlap or
                                             (nextMove.location in {start, target} or
                                              not self.overlaps(nextMove.location, paths))) or \
                        searchType == "A*" and self.validMove(current.location, nextMove.location):

                    neighbor = self.cells[nextMove.location].get()

                    if searchType == "A*":
                        cost = costSoFar[current] + 1

                    else:
                        cost = costSoFar[current] + len(self.paths[(current.location, neighbor.location)].get())

                    if neighbor not in costSoFar or cost < costSoFar[neighbor]:
                        counter += 1

                        costSoFar[neighbor] = cost

                        priority = cost + self.h_cost(neighbor, target, costMethod)

                        frontier.put((priority, counter, neighbor))  # counter acts as tiebreaker in case costs are same

                        cameFrom[neighbor] = current

                        searched.add(neighbor.location)

                else:
                    failed += 1

            if failed == current.numNeighbors:  # returning bc no neighbors
                path.fail()
                return path

            if abort is not None and len(searched) >= abort:  # return bc has searched too many cells w/o finding path
                path.fail()
                return path

        if frontier.empty() and not targetFound:  # nothing valid left to search and target not reached
            altTargetFound = False

            if altTargets is not None:
                for pt in [cellReference.get().location for cellReference in altTargets]:
                    if pt in searched:
                        target = pt
                        altTargetFound = True
                        break

            if not altTargetFound:
                path.fail()

                if not checkOverlap and len(searched) > 0:
                    path.trapped = True

                return path

        toAdd = self.cells[target].obj

        while toAdd != cameFrom[toAdd]:
            path.add(toAdd.location)
            toAdd = cameFrom[toAdd]

        path.add(self.cells[start].obj.location)
        path.reverse()

        if searchType == "A*":
            return path

        else:  # search type is HPA*; path found between chunks but still need to fill gaps with precomputed paths
            temp = Path()
            for i in range(len(path) - 1):
                for j in range(len(self.paths[(path[i], path[i + 1])].get()) - 1):
                    temp.add(self.paths[(path[i], path[i + 1])].get()[j])
            temp.add(path.end)
            return temp


class NodeGroup:
    """Generates nxn nodes and fills with cells, makes neighbors for nodes"""

    def __init__(self, numNodes, cellsInNode):
        self.nodes = {}
        self.cellsInNode = cellsInNode

        # making nodes
        for nodeRow in range(numNodes[0]):
            for nodeCol in range(numNodes[1]):
                self.add(nodeRow, nodeCol)

                # making cells/ assigning position for cells in each node
                self.nodes[(nodeRow, nodeCol)].generateCells(cellsInNode)

        # adding neighbors to nodes
        for node in self.nodes.values():
            for side in node.neighbors:
                if settings.isInNodeMap(node.location + side):
                    node.neighbors[side] = self.nodes[node.location + side]
                    node.numNeighbors += 1

    def add(self, row, col):
        """adds node to node group"""
        self.nodes[Coord(row, col)] = Node(row, col, self.cellsInNode)

    def __len__(self):
        c = 0
        for _ in self.nodes:
            c += 1
        return c

    def __call__(self, *args):
        if len(args) == 1:
            return self.nodes[args[0]]
        else:
            return self.nodes[Coord(args[0], args[1])]

    def __iter__(self):
        return self.nodes.values().__iter__()

    def __repr__(self):
        output = "AllNodes:\n"
        for node in self.nodes:
            output += "\t" + str(self.nodes[node]) + "\n\n"
        return output


class Node:
    """nxn collection of cells, has distinct sides with ability to connect with other nodes"""

    def __init__(self, row, col, cellsInNode):
        self.cells = {}
        self.cellsInNode = cellsInNode

        self.location = Coord(row, col)
        self.x = row
        self.y = col

        self.gates = set()
        self.combos = set()
        self.paths = {}

        self.numNeighbors = 0

        self.neighbors = {
            Coord(0, -1): None,
            Coord(1, 0): None,
            Coord(0, 1): None,
            Coord(-1, 0): None
        }

        self.sides = {
            "top": NodeSide("top", cellsInNode),
            "right": NodeSide("right", cellsInNode),
            "down": NodeSide("down", cellsInNode),
            "left": NodeSide("left", cellsInNode)
        }

        # assigning which position node is in relative to map, offsets used to generate cells in node
        if self.location == (0, 0):
            self.place = "corner"
            self.xOffset = 0
            self.yOffset = 0

        elif self.x == 0 and self.y != 0:
            self.place = "left"
            self.xOffset = 0
            self.yOffset = 1

        elif self.x != 0 and self.y == 0:
            self.place = "top"
            self.xOffset = 1
            self.yOffset = 0

        else:
            self.place = "center"
            self.xOffset = 1
            self.yOffset = 1

    def add(self, row, col):
        """adds cell to node"""
        self.cells[Coord(row, col)] = Cell(row, col)

    def generateCells(self, cellsInNode):
        """creates cells for node, cells vary depending on position of node relative to map"""
        for x in range(cellsInNode[0] + 1 - self.xOffset):
            for y in range(cellsInNode[1] + 1 - self.yOffset):
                self.add(self.x * cellsInNode[0] + x + self.xOffset,
                         self.y * cellsInNode[1] + y + self.yOffset)

                self.cells[self.x * cellsInNode[0] + x + self.xOffset,
                           self.y * cellsInNode[1] + y + self.yOffset].node = self.location

        for x in range(cellsInNode[0] + 1 - self.xOffset):
            for y in range(cellsInNode[1] + 1 - self.yOffset):

                if x == cellsInNode[0] - 1:
                    self.sides["right"].addCell(
                        Reference(self(self.x * cellsInNode[0] + x + 1,
                                       self.y * cellsInNode[1] + y + self.yOffset)))

                if y == cellsInNode[1] - 1:
                    self.sides["down"].addCell(
                        Reference(self(self.x * cellsInNode[0] + x + self.xOffset,
                                       self.y * cellsInNode[1] + y + 1)))

                if self.place == "corner" or self.place == "top":
                    if y == 0:
                        self.sides["top"].addCell(
                            Reference(self(self.x * cellsInNode[0] + x + self.xOffset,
                                           self.y * cellsInNode[1] + y)))

                if self.place == "corner" or self.place == "left":
                    if x == 0:
                        self.sides["left"].addCell(
                            Reference(self(self.x * cellsInNode[0] + x,
                                           self.y * cellsInNode[1] + y + self.yOffset)))

    def placeGates(self, walls):
        """places gates on sides within node based on walls in node"""
        for side in self.sides.values():  # for each side
            if side.numCells != 0:
                i = 0
                for cellRef in side.cells:
                    if cellRef.get().location in walls:
                        side.hasWalls = True

                        # following adds a gate to either side of wall if position is valid
                        if (i - 1) >= 0:
                            if side.cells[i - 1].get().location not in walls \
                                    and side.cells[i - 1] not in side.gates:
                                side.addGate(side.cells[i - 1].new())
                        if (i + 1) < side.numCells:
                            if side.cells[i + 1].get().location not in walls \
                                    and side.cells[i + 1].get() not in side.gates:
                                side.addGate(side.cells[i + 1].new())
                    i += 1

                # if side has no walls, put a gate in the middle of side
                if side.numGates == 0 and not side.hasWalls:
                    side.addGate(side.cells[int(side.numCells / 2)].new())

    def connectNode(self):
        """connect node with neighboring nodes by adding their bottom and right gates to this node's gates"""
        # consolidate all gates for easier access
        for side in self.sides.values():
            for gate in side.gates:
                if gate.get().location not in [cell.get().location for cell in self.gates]:
                    self.gates.add(gate)

        # if has top neighbor, add top neighbor's gates from its bottom side to this node's top side
        if self.neighbors[(0, -1)] is not None:
            for gate in self.neighbors[(0, -1)].sides["down"].gates:
                if gate.get().location not in [cell.get().location for cell in self.gates]:
                    self.gates.add(gate)
                    self.sides["top"].addGate(gate)

        # if has left neighbor, add left neighbor's gates from its right side to this node's left side
        if self.neighbors[(-1, 0)] is not None:
            for gate in self.neighbors[(-1, 0)].sides["right"].gates:
                if gate.get().location not in [cell.get().location for cell in self.gates]:
                    self.gates.add(gate)
                    self.sides["left"].addGate(gate)

    def makeCombos(self):
        """generate all possible combinations of gates from this node"""
        temp = [gate.obj.location for gate in self.gates]
        for combo in combinations(temp, 2):
            self.combos.add(combo)

    def __call__(self, *args):
        if len(args) == 1:

            return self.cells[args[0]]
        else:
            return self.cells[Coord(args[0], args[1])]

    def __iter__(self):
        return self.cells.values().__iter__()

    def __repr__(self):
        output = "Node: " + str(self.location) + "\n\t\tNeighbors: " + "\n\t\tCells" + str(
            [self.cells[cell] for cell in self.cells])
        return output


class NodeSide:
    """represents top, right, bottom, or left side of node, used to make gates and access neighboring nodes"""

    def __init__(self, position, cellsInNode):
        self.position = position

        self.cells = []
        self.gates = []

        self.numGates = 0
        self.numCells = 0

        self.hasWalls = False

        # border indicates side as a coord
        if position == "left":
            self.length = cellsInNode[1]
            self.border = Coord(-1, 0)
            self.opposite = "right"

        elif position == "right":
            self.length = cellsInNode[1]
            self.border = Coord(1, 0)
            self.opposite = "left"

        elif position == "top":
            self.length = cellsInNode[0]
            self.border = Coord(0, -1)
            self.opposite = "down"

        elif position == "down":
            self.length = cellsInNode[0]
            self.border = Coord(0, 1)
            self.opposite = "top"

    def addCell(self, cell):
        """adds cell to side, usually as reference"""
        self.cells.append(cell)
        self.numCells += 1

    def addGate(self, cell):
        """adds gate to side, usually as reference"""
        self.gates.append(cell)
        self.numGates += 1

    def removeGate(self, cell):
        """removes gate from gates"""
        if cell in self.gates:
            self.gates.remove(cell)
            self.numGates -= 1
        else:
            raise ValueError("Cell not in gates...")

    def __hash__(self):
        return hash(self.position)

    def __contains__(self, item):
        return item in [cell.get().location for cell in self.cells]

    def __repr__(self):
        return self.position


class Cell:
    """rectangle representing coord, has neighbors"""
    sides = None

    def __init__(self, row, col):
        self.location = Coord(row, col)
        self.x = row
        self.y = col

        self.node = None
        self.numNeighbors = 0

        Cell.sides = {Coord(1, 0), Coord(-1, 0), Coord(0, -1), Coord(0, 1), Coord(-1, 1), Coord(1, 1), Coord(1, -1),
                      Coord(-1, -1)}

        self.neighbors = {
            "A*": set(),
            "allHPA*": set(),
            "HPA*": set()
        }

        self.refCount = 0

    def __repr__(self):
        output = "Cell: " + str(self.location)
        return output


class Coord:
    """represents tile on map"""

    def __init__(self, *args, big=False):
        self.isBig = big
        self.isSmall = not big

        if len(args) == 2:
            self.x = args[0]
            self.y = args[1]

        else:
            self.x = args[0][0]
            self.y = args[0][1]

    def big(self):
        """make coord 'big', scale position relative to other coords to one based on actual pixels"""
        return Coord(self.x * settings.gridSize[0], self.y * settings.gridSize[1], big=True)

    def small(self):
        """make coord 'small', scale position based on actual pixels to one relative to other coords"""
        return Coord(self.x // settings.gridSize[0], self.y // settings.gridSize[1])

    def normalize(self):
        """if coord is big, snap it to top left corner of tile its in"""
        if self.isBig:
            return Coord(self.x // settings.gridSize[0] * settings.gridSize[0],
                         self.y // settings.gridSize[1] * settings.gridSize[1], big=True)
        else:
            raise ValueError("Can't normalize small point...")

    def set(self, x, y, big=False):
        """sets coord"""
        self.x = x
        self.y = y
        self.isBig = big

    def getNode(self):
        """return location of node that coord is a part of"""
        if self.x <= settings.cellsInNode[0]:
            xCoord = 0
        else:
            xCoord = int((self.x - 1) // settings.cellsInNode[0])

        if self.y <= settings.cellsInNode[1]:
            yCoord = 0
        else:
            yCoord = int((self.y - 1) // settings.cellsInNode[1])

        return Coord(xCoord, yCoord)

    def __add__(self, other):
        """adds x and y coord, retains isBig attribute"""
        if type(other) == Coord:
            return Coord(self.x + other.x, self.y + other.y, big=self.isBig)
        else:
            return Coord(self.x + other[0], self.y + other[1], big=self.isBig)

    def __sub__(self, other):
        """subtracts x and y coord, retains isBig attribute"""
        if type(other) == Coord:
            return Coord(self.x - other.x, self.y - other.y, big=self.isBig)
        else:
            return Coord(self.x - other[0], self.y - other[1], big=self.isBig)

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        """equal if x and y positions are equal and have same isBig if comparing to coord"""
        if type(other) == Coord:
            if (self.x == other.x) and (self.y == other.y) and self.isBig == other.isBig:
                return True
            else:
                return False
        else:
            if (self.x == other[0]) and (self.y == other[1]):
                return True
            else:
                return False

    def __repr__(self):
        return "(" + str(self.x) + ", " + str(self.y) + ")"


class Path(list):
    """stores path to be traversed as list"""

    def __init__(self, path=None):
        list.__init__(self)
        if path is None:
            self.start = None
            self.end = None
        else:
            for pt in path:
                self.append(pt)
            self.start = path[0]
            self.end = path[-1]

        self.failed = False
        self.trapped = False

        self.refCount = 0

    def add(self, coord):
        """adds point to end of path"""
        self.append(coord)
        self.end = coord

        if len(self) == 1:
            self.start = coord

    def reverse(self):
        if len(self) > 1:
            super().reverse()
            self.start = self[0]
            self.end = self[-1]
        else:
            return self

    def peek(self):
        """returns but does not modify 0th element"""
        return self[0]

    def fail(self):
        """flags path as unsuccessful"""
        self.failed = True

    def isEmpty(self):
        """True if no elements in path"""
        return len(self) == 0

    def get(self):
        """returns and removes 0th element in path"""
        value = self.pop(0)
        if len(self) > 0:
            self.start = self[0]
        return value

    def extend(self, path):
        """appends all element in path to self"""
        for pt in path:
            self.append(pt)

        if path.trapped:
            self.trapped = True

        self.end = self[-1]


class CoordMap(dict):
    """contains coords for every cell in map, assigns boolean values to each coord"""

    def __init__(self):
        dict.__init__(self)
        self.size = 0

        for x in range(settings.numCells[0]):
            for y in range(settings.numCells[1]):
                self[Coord(x, y)] = False
                self.size += 1

    def percentFull(self):
        """percentage of cells whole value is True"""
        c = 0
        for pt in self.values():
            if pt:
                c += 1
        return c / self.size * 100


class Reference:
    """allows for pointer-like behavior and allows modifying a local attribute having a global effect"""

    def __init__(self, obj):
        self.obj = obj
        self.obj.refCount += 1

    def get(self):
        """returns actual object"""
        return self.obj

    def set(self, obj):
        """sets object"""
        self.obj.refCount -= 1
        self.obj = obj
        self.obj.refCount += 1

    def new(self):
        """returns a new reference"""
        return Reference(self.obj)

    def __repr__(self):
        return self.obj.__repr__()
