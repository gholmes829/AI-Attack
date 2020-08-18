"""
Testing related to timing and time related performance
"""

import cProfile


def timeFunc(func):
    """times and profiles function"""
    pr = cProfile.Profile()
    pr.enable()
    func()
    pr.disable()
    pr.print_stats(sort='cumulative')
