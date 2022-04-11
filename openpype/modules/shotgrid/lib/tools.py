from functools import wraps


def memoize(function):
    memo = {}

    @wraps(function)
    def wrapper(*args):
        try:
            return memo[args]
        except KeyError:
            rv = function(*args)
            memo[args] = rv
            return rv

    return wrapper
