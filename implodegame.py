#!/usr/bin/env python
#
# Copyright (C) 2007, Joseph C. Lee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import logging
_logger = logging.getLogger('implode-activity.implodegame')

from gettext import gettext as _

import gobject
import gtk
import random
import time

import board
import boardgen
import gridwidget

# A list of the animation stages in order, along with time on-screen (in
# seconds per tick).
_ANIM_TIME_LIST = (
    (gridwidget.ANIMATE_SHRINK, 0.1),
    (gridwidget.ANIMATE_FALL,   0.1),
    (gridwidget.ANIMATE_SLIDE,  0.1),
    (gridwidget.ANIMATE_ZOOM,   0.1),
)
_ANIM_MODES = [x[0] for x in _ANIM_TIME_LIST]
_ANIM_TIMES = dict(_ANIM_TIME_LIST)

# Win animation time on screen (in seconds per tick).
_WIN_ANIM_TIME = 0.04

# Animation timer interval (in msec)
_TIMER_INTERVAL = 20

class ImplodeGame(gtk.EventBox):
    """Gtk widget for playing the implode game."""

    def __init__(self, *args, **kwargs):
        super(ImplodeGame, self).__init__(*args, **kwargs)
        self._animate = True
        self._animation_mode = gridwidget.ANIMATE_NONE
        self._start_time = 0.0

        self._board = None
        self._undoStack = []
        self._redoStack = []

        self._random = random.Random()
        #self._random.seed(0)
        self._difficulty = 0
        self._size = (8, 6)
        self._contiguous = None
        self._seed = 0
        self._fragmentation = 0

        self._animating = False
        self._end_anim_func = None

        self._grid = gridwidget.GridWidget()
        self._grid.connect('piece-selected', self._piece_selected_cb)
        self._grid.connect('undo-key-pressed', self._undo_key_pressed_cb)
        self._grid.connect('redo-key-pressed', self._redo_key_pressed_cb)
        self._grid.connect('new-key-pressed', self._new_key_pressed_cb)
        self.add(self._grid)

        self.new_game()

    def grab_focus(self):
        self._grid.grab_focus()
        self._grid.select_center_cell()

    def new_game(self):
        _logger.debug('New game.')
        self._finish_animation()
        self._seed = self._random.randint(0, 99999)
        size_frag_dict = {
            0: (( 8,  6), 0),
            1: ((12, 10), 0),
            2: ((20, 15), 2),
        }
        (self._size, self._fragmentation) = size_frag_dict[self._difficulty]
        self._reset_board()

    def replay_game(self):
        self._finish_animation()
        _logger.debug('Replay game.')
        self._reset_board()

    def undo(self):
        _logger.debug('Undo.')
        self._finish_animation()
        if len(self._undoStack) == 0:
            return

        self._redoStack.append(self._board)
        self._board = self._undoStack.pop()

        # Force board refresh.
        self._grid.set_board(self._board)
        self._grid.set_win_draw_flag(False)

    def redo(self):
        _logger.debug('Redo.')
        self._finish_animation()
        if len(self._redoStack) == 0:
            return

        self._undoStack.append(self._board)
        self._board = self._redoStack.pop()

        # Force board refresh.
        self._grid.set_board(self._board)

    def set_level(self, level):
        self._difficulty = level

    def get_game_state(self):
        # Returns a dictionary containing the game state, in atomic subobjects.
        def encode_board(b):
            (w, h) = (b.width, b.height)
            data = []
            for i in range(h):
                for j in range(w):
                    data.append(b.get_value(j, i))
            return [w, h] + data
        return {
            'difficulty' : self._difficulty,
            'seed' : self._seed,
            'size' : self._size,
            'fragmentation' : self._fragmentation,
            'board' : encode_board(self._board),
            'undo_stack': [encode_board(b) for b in self._undoStack],
            'redo_stack': [encode_board(b) for b in self._redoStack],
            'win_draw_flag': self._grid.get_win_draw_flag(),
            'win_color': self._grid.get_win_color(),
        }

    def set_game_state(self, state):
        # Sets the game state using a dictionary of atomic subobjects.
        self._finish_animation()
        def decode_board(state):
            b = board.Board()
            (w, h) = (state[0], state[1])
            data = state[2:]
            for i in range(h):
                for j in range(w):
                    b.set_value(j, i, data.pop(0))
            return b
        self._difficulty = state['difficulty']
        self._seed = state['seed']
        self._size = state['size']
        self._fragmentation = state['fragmentation']
        self._board = decode_board(state['board'])
        self._undoStack = [decode_board(x) for x in state['undo_stack']]
        self._redoStack = [decode_board(x) for x in state['redo_stack']]
        self._grid.set_board(self._board)
        self._grid.set_win_state(state['win_draw_flag'], state['win_color'])

    def _reset_board(self):
        # Regenerates the board with the current seed.
        self._board = boardgen.generate_board(seed=self._seed,
                                              fragmentation=self._fragmentation,
                                              max_size=self._size)
        self._grid.set_board(self._board)
        self._grid.set_win_draw_flag(False)
        self._undoStack = []
        self._redoStack = []

    def _piece_selected_cb(self, widget, x, y):
        # Handles piece selection.
        self._finish_animation()
        contiguous = self._board.get_contiguous(x, y)
        if len(contiguous) >= 3:
            self._contiguous = contiguous
            if not self._animate:
                self._remove_contiguous()
            else:
                self._start_time = time.time()
                self._animation_mode = 0
                self._grid.set_removal_block_set(contiguous)
                self._grid.set_animation_mode(_ANIM_MODES[0])
                self._grid.set_animation_percent(0.0)
                self._animating = True
                self._end_anim_func = self._end_removal_animation
                gobject.timeout_add(_TIMER_INTERVAL, self._removal_timer)

    def _undo_key_pressed_cb(self, widget, dummy):
        self.undo()

    def _redo_key_pressed_cb(self, widget, dummy):
        self.redo()

    def _new_key_pressed_cb(self, widget, dummy):
        # Only invoke new command via game pad if board is clear, to prevent
        # terrible accidents.
        if self._board.is_empty():
            self.new_game()

    def _finish_animation(self):
        if self._end_anim_func:
            temp_animate = self._animate
            self._animate = False
            self._end_anim_func()
            self._animate = temp_animate

    def _remove_contiguous(self):
        self._redoStack = []
        self._undoStack.append(self._board.clone())
        self._board.clear_pieces(self._contiguous)
        self._board.drop_pieces()
        self._board.remove_empty_columns()

        # Force board refresh.
        self._grid.set_board(self._board)

        if self._board.is_empty():
            if not self._animate:
                self._init_win_state()
            else:
                self._start_time = time.time()
                self._grid.set_animation_mode(gridwidget.ANIMATE_WIN)
                self._grid.set_animation_percent(0.0)
                self._animating = True
                self._end_anim_func = self._end_win_animation
                gobject.timeout_add(_TIMER_INTERVAL, self._win_timer)
        else:
            contiguous = self._board.get_all_contiguous()
            if len(contiguous) == 0:
                self._init_lose_state()

    def _init_win_state(self):
        self._grid.set_win_draw_flag(True)
        # Clear the undo stack so that the undo/redo buttons do nothing after
        # winning.
        self._undoStack = []

    def _init_lose_state(self):
        pass

    def _win_timer(self):
        if not self._animating:
            return False
        delta = time.time() - self._start_time
        total = _WIN_ANIM_TIME * self._grid.get_animation_length()
        if total > 0:
            percent = float(delta) / total
            if percent < 1.0:
                self._grid.set_animation_percent(percent)
                return True
        self._end_win_animation()
        return False

    def _end_win_animation(self):
        self._animating = False
        self._end_anim_func = None
        self._grid.set_animation_mode(gridwidget.ANIMATE_NONE)
        self._init_win_state()

    def _removal_timer(self):
        if not self._animating:
            return False
        delta = time.time() - self._start_time
        total = (_ANIM_TIMES[_ANIM_MODES[self._animation_mode]]
                 * self._grid.get_animation_length())
        if total > 0:
            percent = float(delta) / total
            if percent < 1.0:
                self._grid.set_animation_percent(percent)
                return True
        self._animation_mode += 1
        if self._animation_mode >= len(_ANIM_MODES):
            self._end_removal_animation()
            return False
        else:
            self._grid.set_animation_mode(_ANIM_MODES[self._animation_mode])
            self._grid.set_animation_percent(0.0)
            self._start_time = time.time()
            return True

    def _end_removal_animation(self):
        self._animating = False
        self._end_anim_func = None
        self._grid.set_animation_mode(gridwidget.ANIMATE_NONE)
        self._remove_contiguous()
