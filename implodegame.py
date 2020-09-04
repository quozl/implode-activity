#!/usr/bin/python3
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

from gi.repository import Gtk
from gi.repository import GObject
import random
import time

from anim import Anim
import board
import boardgen
import gridwidget

# Amount of time to wait after the player is stuck to display the "stuck"
# dialog, in seconds.
_STUCK_DELAY = 0.5

# Amount of time to wait between undos when undoing the board to a solvable
# state after the player gets stuck, in seconds.
_UNDO_DELAY = 0.3


class ImplodeGame(Gtk.EventBox):
    """Gtk widget for playing the implode game."""

    __gsignals__ = {
        'show-stuck': (GObject.SignalFlags.RUN_LAST, None, (int,)),
        'piece-selected': (GObject.SignalFlags.RUN_LAST, None, (int, int)),
        'undo-key-pressed': (GObject.SignalFlags.RUN_LAST, None, (int,)),
        'redo-key-pressed': (GObject.SignalFlags.RUN_LAST, None, (int,)),
        'new-key-pressed': (GObject.SignalFlags.RUN_LAST, None, (int,)),
        'cell-selected': (GObject.SignalFlags.RUN_LAST, None, (int, int)),
    }

    def __init__(self, *args, **kwargs):
        super(ImplodeGame, self).__init__(*args, **kwargs)
        self._animate = True
        self._anim = None

        self._board = None
        # Undo and redo stacks are pairs of (board state, subsequent move).
        self._undo_stack = []
        self._redo_stack = []
        self._winning_moves = []

        self._random = random.Random()
        self._difficulty = 0
        self._size = (8, 6)
        self._fragmentation = 0

        self._grid = gridwidget.GridWidget()
        self._grid.connect('piece-selected', self._piece_selected_cb)
        self._grid.connect('undo-key-pressed', self._undo_key_pressed_cb)
        self._grid.connect('redo-key-pressed', self._redo_key_pressed_cb)
        self._grid.connect('new-key-pressed', self._new_key_pressed_cb)
        self._grid.connect('cell-selected', self._cell_selected_cb)
        self.add(self._grid)

        self._seed = self._random.randint(0, 99999)
        self.new_game()

    def grab_focus(self):
        self._grid.grab_focus()
        # self._grid.select_center_cell()

    def reseed(self):
        self.set_seed(self._random.randint(0, 99999))

    def set_seed(self, seed):
        self._seed = seed
        self._random.seed(self._seed)

    def get_seed(self):
        return self._seed

    def new_game(self):
        self._hide_stuck()
        self._stop_animation()
        size_frag_dict = {
            0: ((8, 6), 0),
            1: ((12, 10), 0),
            2: ((20, 15), 2),
        }
        (self._size, self._fragmentation) = size_frag_dict[self._difficulty]
        self._reset_board()

    def replay_game(self):
        self._hide_stuck()
        self._stop_animation()
        self._reset_board()

    def undo(self):
        self._hide_stuck()
        self._stop_animation()
        if len(self._undo_stack) == 0:
            return

        self._undo_last_move()

    def undo_to_solvable_state(self):
        # Undoes the player's moves until the puzzle is in a solvable state.
        #
        # Actually, we undo moves until the player's moves so far match the
        # beginning of a list of moves known to solve the puzzle, as given by
        # the puzzle generator.  Since each puzzle can potentially be solved
        # through many different sequences of moves, we will almost certainly
        # be undoing more moves than we need to.  One possible improvement
        # would be to write a generic puzzle solver that can test some of the
        # player's later board states for solvability, so that we don't need to
        # undo as many moves.

        self._hide_stuck()
        self._stop_animation()
        if len(self._undo_stack) == 0:
            return

        start_time = time.time()

        def update_func(start_time_ref=[start_time]):
            delta = time.time() - start_time_ref[0]
            if delta > _UNDO_DELAY:
                self._undo_last_move()
                moves = self._get_moves_so_far()
                if moves == self._winning_moves[:len(moves)]:
                    return False
                start_time_ref[0] = time.time()
            return True

        def end_anim_func(anim_stopped):
            moves = self._get_moves_so_far()
            while moves != self._winning_moves[:len(moves)]:
                self._undo_last_move()
                moves = self._get_moves_so_far()

        self._anim = Anim(update_func, end_anim_func)
        self._anim.start()

    def _get_moves_so_far(self):
        # Returns a list of the moves so far.
        return [move for (board, move) in self._undo_stack]

    def _undo_last_move(self):
        # Undoes the most recent move and stores the state on the undo stack.
        (board, move) = self._undo_stack.pop()
        self._redo_stack.append((self._board, move))
        self._board = board

        # Force board refresh.
        self._grid.set_board(self._board)
        self._grid.set_win_draw_flag(False)

    def redo(self):
        self._hide_stuck()
        self._stop_animation()
        if len(self._redo_stack) == 0:
            return

        (board, move) = self._redo_stack.pop()
        self._undo_stack.append((self._board, move))
        self._board = board

        # Force board refresh.
        self._grid.set_board(self._board)

        self._check_for_lose_state()

    def set_level(self, level):
        self._difficulty = level

    def get_game_state(self):
        # Returns a dictionary containing the game state, in atomic subobjects.
        def encode_board(board, move):
            # Encodes the given board and move to a state array.
            (w, h) = (board.width, board.height)
            data = []
            for i in range(h):
                for j in range(w):
                    data.append(board.get_value(j, i))
            if move is not None:
                return [w, h] + data + list(move)
            else:
                return [w, h] + data
        return {
            'difficulty': self._difficulty,
            'seed': self._seed,
            'size': self._size,
            'fragmentation': self._fragmentation,
            'board': encode_board(self._board, None),
            'undo_stack': [encode_board(b, m) for b, m in self._undo_stack],
            'redo_stack': [encode_board(b, m) for b, m in self._redo_stack],
            'win_draw_flag': self._grid.get_win_draw_flag(),
            'win_color': self._grid.get_win_color(),
            'winning_moves': self._winning_moves
        }

    def set_game_state(self, state):
        # Sets the game state using a dictionary of atomic subobjects.
        self._hide_stuck()
        self._stop_animation()

        def decode_board(state):
            # Decodes a board (and maybe an appended move) from the given state
            # array.
            b = board.Board()
            (w, h) = (state[0], state[1])
            data = state[2:]
            for i in range(h):
                for j in range(w):
                    b.set_value(j, i, data.pop(0))
            if len(data) == 2:
                # Return appended move.
                return b, tuple(data)
            else:
                return b, None
        self._difficulty = state['difficulty']
        self.set_seed(state['seed'])
        self._size = state['size']
        self._fragmentation = state['fragmentation']
        (self._board, dummy) = decode_board(state['board'])
        self._undo_stack = [decode_board(x) for x in state['undo_stack']]
        self._redo_stack = [decode_board(x) for x in state['redo_stack']]
        self._grid.set_board(self._board)
        self._grid.set_win_state(state['win_draw_flag'], state['win_color'])
        if 'winning_moves' in state:
            # Prior to version 8, we didn't store the list of winning moves.
            self._winning_moves = [tuple(x) for x in state['winning_moves']]
        else:
            self._winning_moves = []

        self._check_for_lose_state()

    def _reset_board(self):
        # Regenerates the board with the current seed.
        (self._board, self._winning_moves) = \
            boardgen.generate_board(
                seed=self._seed, fragmentation=self._fragmentation,
                max_size=self._size)
        self._grid.set_board(self._board)
        self._grid.set_win_draw_flag(False)
        self._undo_stack = []
        self._redo_stack = []

    def _piece_selected_cb(self, widget, x, y):
        # Handles piece selection.

        # We check contiguous before stopping the animation because we don't
        # want a click on the game board in a losing state to stop the "stuck"
        # animation.
        if len(self._board.get_contiguous(x, y)) < 3:
            return

        self.emit('piece-selected', x, y)
        self.piece_selected(x, y)

    def piece_selected(self, x, y):
        self._hide_stuck()
        self._stop_animation()
        # We recalc contiguous here because _stop_animation may modify board
        # contents (e.g. the undo-many animation).
        contiguous = self._board.get_contiguous(x, y)
        if len(contiguous) >= 3:
            def remove_func(anim_stopped=False):
                self._remove_contiguous(contiguous, anim_stopped)
            if self._animate:
                self._anim = self._grid.get_removal_anim(self._board,
                                                         contiguous,
                                                         remove_func)
                self._anim.start()
            else:
                remove_func()

    def _undo_key_pressed_cb(self, widget, dummy):
        self.emit('undo-key-pressed', dummy)
        self.undo()

    def _redo_key_pressed_cb(self, widget, dummy):
        self.emit('redo-key-pressed', dummy)
        self.redo()

    def _new_key_pressed_cb(self, widget, dummy):
        # Only invoke new command via game pad if board is clear, to prevent
        # terrible accidents.
        if self._board.is_empty():
            self.reseed()
            self.emit('new-key-pressed', self._seed)
            self.new_game()

    def _cell_selected_cb(self, widget, x, y):
        self.emit('cell-selected', x, y)

    def cell_selected(self, key, fg, bg, x, y):
        self._grid.set_others_cells(key, fg, bg, x, y)

    def _stop_animation(self):
        if self._anim is not None:
            self._anim.stop()

    def _remove_contiguous(self, contiguous, anim_stopped=False):
        # Removes the given set of contiguous blocks from the board.
        self._redo_stack = []
        # We save the player's move as the lexographically smallest coordinate
        # of the piece.
        move = min(contiguous)
        self._undo_stack.append((self._board.clone(), move))
        self._board.clear_pieces(contiguous)
        self._board.drop_pieces()
        self._board.remove_empty_columns()

        # Force board refresh.
        self._grid.set_board(self._board)

        if self._board.is_empty():
            if self._animate and not anim_stopped:
                self._anim = self._grid.get_win_anim(self._init_win)
                self._anim.start()
            else:
                self._init_win()
        else:
            self._check_for_lose_state()

    def _check_for_lose_state(self):
        if not self._board.is_empty():
            all_contiguous = self._board.get_all_contiguous()
            if len(all_contiguous) == 0:
                self._init_lose()

    def _init_win(self, anim_stopped=False):
        self._grid.set_win_draw_flag(True)
        # Clear the undo stack so that the undo/redo buttons do nothing after
        # winning.
        self._undo_stack = []

    def _init_lose(self):
        # If the player is stuck, wait a little while, then signal the activity
        # to display the stuck dialog.
        start_time = time.time()

        def update_func():
            delta = time.time() - start_time
            return (delta <= _STUCK_DELAY)

        def end_anim_func(anim_stopped):
            if not anim_stopped:
                self.emit('show-stuck', 1)

        self._anim = Anim(update_func, end_anim_func)
        self._anim.start()

    def _hide_stuck(self):
        self.emit('show-stuck', 0)
