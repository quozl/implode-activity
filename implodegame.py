#!/usr/bin/env python
#
# Copyright (C) 2007-2009, Joseph C. Lee
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

import gtk
import random

import board
import boardgen
import gridwidget


class ImplodeGame(gtk.EventBox):
    """Gtk widget for playing the implode game."""

    def __init__(self, *args, **kwargs):
        super(ImplodeGame, self).__init__(*args, **kwargs)
        self._animate = True
        self._current_anim = None

        self._board = None
        self._undo_stack = []
        self._redo_stack = []

        self._random = random.Random()
        #self._random.seed(0)
        self._difficulty = 0
        self._size = (8, 6)
        self._contiguous = None
        self._seed = 0
        self._fragmentation = 0

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
        self._stop_animation()
        self._seed = self._random.randint(0, 99999)
        size_frag_dict = {
            0: (( 8,  6), 0),
            1: ((12, 10), 0),
            2: ((20, 15), 2),
        }
        (self._size, self._fragmentation) = size_frag_dict[self._difficulty]
        self._reset_board()

    def replay_game(self):
        self._stop_animation()
        _logger.debug('Replay game.')
        self._reset_board()

    def undo(self):
        _logger.debug('Undo.')
        self._stop_animation()
        if len(self._undo_stack) == 0:
            return

        self._redo_stack.append(self._board)
        self._board = self._undo_stack.pop()

        # Force board refresh.
        self._grid.set_board(self._board)
        self._grid.set_win_draw_flag(False)

    def redo(self):
        _logger.debug('Redo.')
        self._stop_animation()
        if len(self._redo_stack) == 0:
            return

        self._undo_stack.append(self._board)
        self._board = self._redo_stack.pop()

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
            'undo_stack': [encode_board(b) for b in self._undo_stack],
            'redo_stack': [encode_board(b) for b in self._redo_stack],
            'win_draw_flag': self._grid.get_win_draw_flag(),
            'win_color': self._grid.get_win_color(),
        }

    def set_game_state(self, state):
        # Sets the game state using a dictionary of atomic subobjects.
        self._stop_animation()
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
        self._undo_stack = [decode_board(x) for x in state['undo_stack']]
        self._redo_stack = [decode_board(x) for x in state['redo_stack']]
        self._grid.set_board(self._board)
        self._grid.set_win_state(state['win_draw_flag'], state['win_color'])

    def _reset_board(self):
        # Regenerates the board with the current seed.
        self._board = boardgen.generate_board(seed=self._seed,
                                              fragmentation=self._fragmentation,
                                              max_size=self._size)
        self._grid.set_board(self._board)
        self._grid.set_win_draw_flag(False)
        self._undo_stack = []
        self._redo_stack = []

    def _piece_selected_cb(self, widget, x, y):
        # Handles piece selection.
        self._stop_animation()
        contiguous = self._board.get_contiguous(x, y)
        if len(contiguous) >= 3:
            self._contiguous = contiguous
            if self._animate:
                self._current_anim = self._grid.start_removal_anim(self._remove_contiguous, contiguous)
            else:
                self._remove_contiguous()

    def _undo_key_pressed_cb(self, widget, dummy):
        self.undo()

    def _redo_key_pressed_cb(self, widget, dummy):
        self.redo()

    def _new_key_pressed_cb(self, widget, dummy):
        # Only invoke new command via game pad if board is clear, to prevent
        # terrible accidents.
        if self._board.is_empty():
            self.new_game()

    def _stop_animation(self):
        if self._current_anim is not None:
            self._current_anim.stop()

    def _remove_contiguous(self, anim_stopped=False):
        self._redo_stack = []
        self._undo_stack.append(self._board.clone())
        self._board.clear_pieces(self._contiguous)
        self._board.drop_pieces()
        self._board.remove_empty_columns()

        # Force board refresh.
        self._grid.set_board(self._board)

        if self._board.is_empty():
            if self._animate and not anim_stopped:
                self._current_anim = self._grid.start_win_anim(self._init_win)
            else:
                self._init_win()
        else:
            contiguous = self._board.get_all_contiguous()
            if len(contiguous) == 0:
                self._init_lose()

    def _init_win(self, anim_stopped=False):
        self._grid.set_win_draw_flag(True)
        # Clear the undo stack so that the undo/redo buttons do nothing after
        # winning.
        self._undo_stack = []

    def _init_lose(self):
        pass
