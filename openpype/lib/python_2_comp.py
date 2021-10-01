import weakref


class _weak_callable:
    def __init__(self, obj, func):
        self.im_self = obj
        self.im_func = func

    def __call__(self, *args, **kws):
        if self.im_self is None:
            return self.im_func(*args, **kws)
        else:
            return self.im_func(self.im_self, *args, **kws)


class WeakMethod:
    """ Wraps a function or, more importantly, a bound method in
    a way that allows a bound method's object to be GCed, while
    providing the same interface as a normal weak reference. """

    def __init__(self, fn):
        try:
            self._obj = weakref.ref(fn.im_self)
            self._meth = fn.im_func
        except AttributeError:
            # It's not a bound method
            self._obj = None
            self._meth = fn

    def __call__(self):
        if self._dead():
            return None
        return _weak_callable(self._getobj(), self._meth)

    def _dead(self):
        return self._obj is not None and self._obj() is None

    def _getobj(self):
        if self._obj is None:
            return None
        return self._obj()
