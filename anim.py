import gobject

# Animation timer interval (in msec)
_TIMER_INTERVAL = 20

class Anim(object):
    """Manages an animation."""
    def __init__(self, update_func, end_anim_func):
        """update_func is a function returns True if the animation should
           continue, False otherwise.  end_anim_func is a function that takes a
           boolean indicating whether the animation was stopped prematurely."""
        self._update_func = update_func
        self._end_anim_func = end_anim_func
        self._animating = False

    def start(self):
        self._animating = True
        self._update_func()
        gobject.timeout_add(_TIMER_INTERVAL, self._timer)

    def stop(self):
        if self._animating:
            self._end_anim(anim_stopped=True)

    def _timer(self):
        if not self._animating:
            return False
        if self._update_func():
            return True
        self._end_anim(anim_stopped=False)
        return False

    def _end_anim(self, anim_stopped):
        self._animating = False
        self._end_anim_func(anim_stopped=anim_stopped)



