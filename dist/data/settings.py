"""
Author: Grant Holmes
Contact: g.holmes429@gmail.com
Date: 08/16/2020

Basic settings for game setup
"""

screenSize = (800, 615)
mapSize = (615, 615)
sidePanel = (185, 615)

numNodes = (8, 8)
cellsInNode = (5, 5)

numCells = (numNodes[0] * cellsInNode[0] + 1, numNodes[1] * cellsInNode[1] + 1)
gridSize = (int(mapSize[0] / numCells[0]), int(mapSize[0] / numCells[0]))

gameName = "AI Attack!"

targetFrameRate = 60
normalizedFrameRate = 60


def isInCellMap(coord):
    """returns true if coord is in bounds of map dictated by settings"""
    if 0 <= coord.x < numCells[0] and 0 <= coord.y < numCells[1]:
        return True
    else:
        return False


def isInNodeMap(coord):
    """returns true if coord is in bounds of map dictated by settings"""
    if 0 <= coord.x < numNodes[0] and 0 <= coord.y < numNodes[1]:
        return True
    else:
        return False
