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
_logger = logging.getLogger('implode-activity.gridwidget')

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
import math
import random
import time

import color

from keymap import KEY_MAP
from anim import Anim

# Color of the background.
_BG_COLOR = (0.35, 0.35, 0.7)

# Color of the selection border.
_SELECTED_COLOR = (1.0, 1.0, 1.0)

# Ratio of the width/height (whichever is smaller) to leave as a margin
# around the playing board.
_BORDER = 0.05

# Ratio of the cell width to leave as a space between blocks.
_BLOCK_GAP = 0.1

# Ratio of the cell width to overdraw the selection border.
_SELECTED_MARGIN = 0.1

# Ratio of the cell width to use for the radius of the selection cursor circle.
_SELECTED_DOT_RADIUS = 0.1

# Smiley face.
_SMILEY = """
    ..xxxxxx..
    .x......x.
    x........x
    x..x..x..x
    x........x
    x.x....x.x
    x..xxxx..x
    .x......x.
    ..xxxxxx..
"""

# Removal animation stages.
_ANIM_STAGE_NONE = 0
_ANIM_STAGE_SHRINK = 1
_ANIM_STAGE_FALL = 2
_ANIM_STAGE_ZOOM = 3

_ANIM_STAGES = [
    _ANIM_STAGE_NONE,
    _ANIM_STAGE_SHRINK,
    _ANIM_STAGE_FALL,
    _ANIM_STAGE_ZOOM,
]

# Animation time scaling factor (in seconds per tick).
_ANIM_SCALE = 0.04

# import traceback
# def _log_errors(func):
#     # A function decorator to add error logging to selected functions.
#     # (For when GTK eats exceptions).
#     def wrapper(*args, **kwargs):
#         try:
#             return func(*args, **kwargs)
#         except:
#             _logger.debug(traceback.format_exc())
#             raise
#     return wrapper


def _log_errors(func):
    return func


class GridWidget(Gtk.DrawingArea):
    """Gtk widget for rendering the game board."""

    __gsignals__ = {
        'piece-selected': (GObject.SignalFlags.RUN_LAST, None, (int, int)),
        'undo-key-pressed': (GObject.SignalFlags.RUN_LAST, None, (int,)),
        'redo-key-pressed': (GObject.SignalFlags.RUN_LAST, None, (int,)),
        'new-key-pressed': (GObject.SignalFlags.RUN_LAST, None, (int,)),
    }

    def __init__(self, *args, **kwargs):
        super(GridWidget, self).__init__(*args, **kwargs)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.KEY_PRESS_MASK)
        self.set_can_focus(True)

        self._board_drawer = BoardDrawer(self._get_size, self._invalidate_rect)
        self._win_drawer = WinDrawer(self._get_size, self._invalidate_rect)
        self._removal_drawer = RemovalDrawer(
            self._get_size, self._invalidate_rect)
        self._set_current_drawer(self._board_drawer)

        self.connect('draw', self._draw_event_cb)
        self.connect('configure-event', self._configure_event_cb)
        self.connect('button-press-event', self._button_press_event_cb)

    def _get_size(self):
        return (self.get_allocated_width(), self.get_allocated_height())

    def _invalidate_rect(self, rect):
        if self.get_window():
            self.get_window().invalidate_rect(rect, True)

    def set_board(self, board):
        self._board_drawer.set_board(board)

    def set_win_draw_flag(self, value):
        drawing_win = self.get_win_draw_flag()
        if value != drawing_win:
            if value:
                self._set_current_drawer(self._win_drawer)
            else:
                self._set_current_drawer(self._board_drawer)
            self._invalidate_board()

    def _invalidate_board(self):
        (width, height) = self._get_size()
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = (0, 0, width, height)
        self._invalidate_rect(rect)

    def get_win_draw_flag(self):
        return (self._current_drawer is self._win_drawer)

    def get_win_color(self):
        return self._win_drawer.get_win_color()

    def set_win_state(self, draw_flag, win_color):
        if not draw_flag:
            self._set_current_drawer(self._board_drawer)
        else:
            self._set_current_drawer(self._win_drawer)
            self._win_drawer.set_win_state(draw_flag, win_color)

    def select_center_cell(self):
        self._board_drawer.select_center_cell()

    @_log_errors
    def _button_press_event_cb(self, widget, event):
        # Ignore mouse clicks while animating.
        if self._is_animating():
            return True
        # Ignore double- and triple-clicks.
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return True
        self.grab_focus()
        self._board_drawer.set_mouse_selection(event.x, event.y)
        selected_cell = self._board_drawer.get_selected_cell()
        if selected_cell is not None:
            self.emit('piece-selected', *selected_cell)
        return True

    @_log_errors
    def do_key_press_event(self, event):
        action = KEY_MAP.get(event.keyval, None)
        if (action == 'new') or \
           (action == 'select' and not self._board_drawer.board_is_valid()):
            self.emit('new-key-pressed', 0)
            return True
        # Ignore key presses while animating.
        if self._is_animating():
            return False
        if not self._board_drawer.board_is_valid():
            self._board_drawer.set_selected_cell(None)
            return action is not None
        else:
            selected_cell = self._board_drawer.get_selected_cell()
            if selected_cell is None:
                self._board_drawer.select_center_cell()
                return True
            else:
                if action == 'select':
                    self.emit('piece-selected', *selected_cell)
                elif action == 'undo':
                    self.emit('undo-key-pressed', 0)
                elif action == 'redo':
                    self.emit('redo-key-pressed', 0)
                else:
                    offsets = {'up': (0, 1),
                               'down': (0, -1),
                               'left': (-1, 0),
                               'right': (1, 0)}
                    if action in offsets:
                        offset = offsets[action]
                        return self._board_drawer.move_selected_cell(*offset)
                    else:
                        return False

    @_log_errors
    def do_motion_notify_event(self, event):
        # Ignore mouse motion while animating.
        if self._is_animating():
            return
        if event.is_hint:
            (x, y, state) = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
        self._board_drawer.set_mouse_selection(x, y)

    def _draw_event_cb(self, widget, cr):
        alloc = self.get_allocation()
        self._current_drawer.draw(cr, alloc.width, alloc.height)

    @_log_errors
    def _configure_event_cb(self, widget, event):
        self._current_drawer.resize(event.width, event.height)

    def _set_current_drawer(self, drawer):
        self._current_drawer = drawer
        (width, height) = self._get_size()
        self._current_drawer.resize(width, height)

    def _is_animating(self):
        return (self._current_drawer is not self._board_drawer)

    def get_removal_anim(self, board, contiguous, end_anim_func):
        self._set_current_drawer(self._removal_drawer)
        self._removal_drawer.init(board, contiguous)
        self._removal_drawer.set_anim_time(0.0)
        start_time = time.time()

        def update_func(start_time_ref=[start_time]):
            delta = time.time() - start_time_ref[0]
            length = self._removal_drawer.get_anim_length()
            if delta > length:
                if not self._removal_drawer.next_stage():
                    return False
                start_time_ref[0] = time.time()
                delta = 0.0
            self._removal_drawer.set_anim_time(delta)
            return True

        def local_end_anim_func(anim_stopped):
            self._set_current_drawer(self._board_drawer)
            end_anim_func(anim_stopped)

        return Anim(update_func, local_end_anim_func)

    def get_win_anim(self, end_anim_func):
        self._set_current_drawer(self._win_drawer)
        self._win_drawer.init()
        length = self._win_drawer.get_anim_length()
        start_time = time.time()

        def update_func():
            delta = time.time() - start_time
            self._win_drawer.set_anim_time(min(delta, length))
            return (delta <= length)

        def local_end_anim_func(anim_stopped):
            self._win_drawer.set_anim_time(length)
            end_anim_func(anim_stopped)

        return Anim(update_func, local_end_anim_func)


# NOTE: We separate the drawing/interaction code from the GTK widget code so
# that we can reuse the drawing in a widget that draws more on top; apparently
# GTK doesn't like overlapping widgets.

class BoardDrawer(object):
    """Object to manage drawing of the game board."""

    def __init__(self, get_size_func, invalidate_rect_func, *args, **kwargs):
        super(BoardDrawer, self).__init__(*args, **kwargs)
        self._board = None
        self._board_width = 0
        self._board_height = 0
        self._selected_cell = None
        self._contiguous_map = {}

        # Drawing offset and scale.
        self._board_transform = None

        # Callback functions set by owner.
        self._get_size_func = get_size_func
        self._invalidate_rect_func = invalidate_rect_func

    def set_board(self, value):
        self._board = value
        self._recalc_board_dimensions()
        self._recalc_contiguous_map()
        (width, height) = self._get_size_func()
        self.resize(width, height)
        if self._selected_cell is not None:
            # If a cell is selected, clamp it to new board boundaries.
            (x, y) = self._selected_cell
            x = max(0, min(self._board_width - 1, x))
            y = max(0, min(self._board_height - 1, y))
            self._selected_cell = (x, y)
        self._invalidate_board()

    def _recalc_contiguous_map(self):
        self._contiguous_map = {}
        if self._board is None:
            return
        all_contiguous = self._board.get_all_contiguous()
        for contiguous in all_contiguous:
            for coord in contiguous:
                self._contiguous_map[coord] = contiguous

    def get_selected_cell(self):
        return self._selected_cell

    def set_selected_cell(self, value):
        self._selected_cell = value

    def select_center_cell(self):
        if not self.board_is_valid():
            return
        if self._selected_cell is not None:
            self._invalidate_selection(self._selected_cell)
        self._selected_cell = (int(self._board_width // 2),
                               self._board_height - 1)
        self._invalidate_selection(self._selected_cell)

    def move_selected_cell(self, x_offset, y_offset):
        # Moves the selected cell in the direction of the given offset,
        # returning True if the cell changed after clamping, False otherwise.
        (x, y) = self._selected_cell
        x = max(0, min(self._board_width - 1, x + x_offset))
        y = max(0, min(self._board_height - 1, y + y_offset))
        if self._selected_cell == (x, y):
            return False
        else:
            self._invalidate_selection(self._selected_cell)
            self._selected_cell = (x, y)
            self._invalidate_selection(self._selected_cell)
            return True

    def set_mouse_selection(self, x, y):
        # Sets the mouse selection to the block corresponding to the given x
        # and y coordinates.
        if not self.board_is_valid():
            self._selected_cell = None
            return
        old_selection = self._selected_cell
        (x1, y1) = self._display_to_cell(x, y)
        if (0 <= x1 < self._board_width and 0 <= y1 < self._board_height):
            self._selected_cell = (x1, y1)
        self._invalidate_selection(old_selection)
        self._invalidate_selection(self._selected_cell)

    def get_block_coord(self, x, y):
        if not self.board_is_valid():
            return (0, 0)
        (block_x, block_y) = self._cell_to_display(x + 0.5, y + 0.5)
        return (block_x, block_y)

    def _invalidate_board(self):
        (width, height) = self._get_size_func()
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = (0, 0, width, height)
        self._invalidate_rect_func(rect)

    def _invalidate_selection(self, selection_coord):
        contiguous = self._contiguous_map.get(selection_coord, None)
        if contiguous is not None and len(contiguous) >= 3:
            self._invalidate_block_set(contiguous, _SELECTED_MARGIN)
        elif selection_coord is not None:
            self._invalidate_block_set(set((selection_coord,)), 0)

    def _invalidate_block_set(self, block_set, margin):
        if len(block_set) == 0:
            return
        x_coords = [q[0] for q in block_set]
        y_coords = [q[1] for q in block_set]
        min_x1 = min(x_coords) - margin
        max_x1 = max(x_coords) + margin + 1
        min_y1 = min(y_coords) - margin
        max_y1 = max(y_coords) + margin + 1
        pt1 = self._cell_to_display(min_x1, min_y1)
        pt2 = self._cell_to_display(max_x1, max_y1)
        min_x2 = math.floor(min(pt1[0], pt2[0])) - 1
        max_x2 = math.ceil(max(pt1[0], pt2[0])) + 1
        min_y2 = math.floor(min(pt1[1], pt2[1])) - 1
        max_y2 = math.ceil(max(pt1[1], pt2[1])) + 1
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = (
            int(min_x2), int(min_y2),
            int(max_x2 - min_x2), int(max_y2 - min_y2))
        self._invalidate_rect_func(rect)

    def _display_to_cell(self, x, y):
        # Converts from display coordinate to a cell coordinate.
        return self._board_transform.inverse_transform(x, y)

    def _cell_to_display(self, x, y):
        # Converts from a cell coordinate to a display coordinate.
        return self._board_transform.transform(x, y)

    def resize(self, width, height):
        if not self.board_is_valid():
            self._board_transform = _BoardTransform()
        else:
            self._board_transform = _BoardTransform()
            self._board_transform.setup(width, height, self._board_width,
                                        self._board_height)

    def draw(self, cr, width, height):
        # Draws the widget.
        _draw_background(cr, width, height)
        cr.save()
        self._board_transform.set_up_cairo(cr)
        self._draw_board(cr)
        cr.restore()

    def _draw_board(self, cr):
        # Draws the game board on the widget, where each unit corresponds to
        # a cell on the board.
        self._draw_blocks(cr)
        self._draw_selected(cr)
        self._draw_selected_dot(cr)

    def _draw_blocks(self, cr):
        if not self.board_is_valid():
            return

        value_map = self._board.get_value_map()
        for (coord, value) in list(value_map.items()):
            self._draw_block(cr, coord[0], coord[1], value)

    def _draw_selected(self, cr):
        # Draws a white background to selected blocks, then redraws blocks
        # on top.
        if (self._selected_cell is None or
                self._selected_cell not in self._contiguous_map):
            return
        contiguous = self._contiguous_map[self._selected_cell]
        value = self._board.get_value(*self._selected_cell)
        cr.set_source_rgb(*_SELECTED_COLOR)
        for (x, y) in contiguous:
            self._draw_square(cr, x, y, _SELECTED_MARGIN)
        for (x, y) in contiguous:
            self._draw_block(cr, x, y, value)

    def _draw_block(self, cr, x, y, value):
        # Draws the block at the given grid cell.
        assert value is not None
        c = color.colors[value]
        cr.set_source_rgb(*c)
        self._draw_square(cr, x, y, -_BLOCK_GAP)

    def _draw_square(self, cr, x, y, margin):
        # Draws a square in the given grid cell with the given margin.
        x1 = float(x) - margin
        y1 = float(y) - margin
        size = 1.0 + margin * 2
        cr.rectangle(x1, y1, size, size)
        cr.fill()

    def _draw_selected_dot(self, cr):
        if self._selected_cell is None:
            return
        # Draws a dot indicating the selected cell.
        cr.set_source_rgb(*_SELECTED_COLOR)

        (x, y) = self._selected_cell
        cr.arc(x + 0.5, y + 0.5, _SELECTED_DOT_RADIUS, 0, math.pi * 2.0)
        cr.fill()

    def _recalc_board_dimensions(self):
        if self.board_is_valid():
            self._board_width = self._board.width
            self._board_height = self._board.height
        else:
            self._board_width = 1
            self._board_height = 1

    def board_is_valid(self):
        # Returns True if the board is set and has valid dimensions (>=1).
        return (self._board is not None and not self._board.is_empty())


class RemovalDrawer(object):
    """Object to manage the drawing of the animation of removing blocks."""

    def __init__(self, get_size_func, invalidate_rect_func, *args, **kwargs):
        super(RemovalDrawer, self).__init__(*args, **kwargs)
        self._board = None
        self._board_width = 0
        self._board_height = 0
        self._removal_block_set = set()
        self._anim_time = 0.0
        self._anim_stage = _ANIM_STAGE_SHRINK

        # Game animation variables.
        self._anim_coords = []
        self._anim_frames = {}
        self._anim_lengths = {}

        # Drawing offset and scale.
        self._board_transform = _BoardTransform()

        # Callback functions set by owner.
        self._get_size_func = get_size_func
        self._invalidate_rect_func = invalidate_rect_func

    def init(self, board, removal_block_set):
        self._board = board
        self._recalc_board_dimensions()
        self._removal_block_set = removal_block_set
        self._anim_stage = _ANIM_STAGE_SHRINK
        self._recalc_game_anim_frames()
        self._recalc_anim_coords()
        self._invalidate_board()

    def next_stage(self):
        """Sets the current animation stage; returns False if there are no
           more stages, True otherwise."""
        stage = self._anim_stage + 1
        while stage < len(self._anim_lengths) and \
                not self._anim_lengths[stage]:
            stage += 1
        if stage == len(self._anim_lengths):
            return False
        self._anim_stage = stage
        self._invalidate_board()
        return True

    def set_anim_time(self, value):
        """Sets the time passed for the current stage."""
        self._anim_time = value
        self._recalc_anim_coords()
        self._invalidate_board()

    def get_anim_length(self):
        """Returns the length of the current stage in seconds."""
        return self._anim_lengths[self._anim_stage]

    def _invalidate_board(self):
        (width, height) = self._get_size_func()
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = (0, 0, width, height)
        self._invalidate_rect_func(rect)

    def _recalc_game_anim_frames(self):
        if not self.board_is_valid():
            self._anim_frames = {}
            self._anim_lengths = {}
            return

        (width, height) = self._get_size_func()
        transform = _BoardTransform()
        transform.setup(width,
                        height,
                        self._board_width,
                        self._board_height)

        frames = {}
        lengths = {}

        # Calculate starting coords.
        starting_frame = []
        value_map = self._board.get_value_map()
        for ((i, j), value) in list(value_map.items()):
            starting_frame.append((i, j, 1.0, value))
        frames[_ANIM_STAGE_NONE] = (transform, starting_frame)
        lengths[_ANIM_STAGE_NONE] = 0.0

        # Calculate shrinking coords.
        shrinking_frame = []
        for (i, j, scale, value) in starting_frame:
            if (i, j) in self._removal_block_set:
                shrinking_frame.append((i, j, 0.0, value))
            else:
                shrinking_frame.append((i, j, scale, value))
        frames[_ANIM_STAGE_SHRINK] = (transform, shrinking_frame)
        if len(self._removal_block_set) > 0:
            lengths[_ANIM_STAGE_SHRINK] = 3 * _ANIM_SCALE
        else:
            lengths[_ANIM_STAGE_SHRINK] = 0.0

        # Calculate falling coords.
        falling_frame = []
        board2 = self._board.clone()
        board2.clear_pieces(self._removal_block_set)
        drop_map = board2.get_drop_map()
        max_change = 0
        for (i, j, scale, value) in shrinking_frame:
            coord = drop_map.get((i, j), None)
            if coord is None:
                falling_frame.append((i, j, scale, value))
            else:
                falling_frame.append((coord[0], coord[1], scale, value))
                max_change = max(max_change, j - coord[1])
        frames[_ANIM_STAGE_FALL] = (transform, falling_frame)
        if max_change > 0:
            lengths[_ANIM_STAGE_FALL] = 3 * _ANIM_SCALE
        else:
            lengths[_ANIM_STAGE_FALL] = 0.0

        # Calculate sliding/zooming coords.
        zooming_frame = []
        board2.drop_pieces()
        slide_map = board2.get_slide_map()
        max_change = 0
        board2.remove_empty_columns()
        board_width2 = board2.width
        board_height2 = board2.height
        for(i, j, scale, value) in falling_frame:
            if i in slide_map:
                zooming_frame.append((slide_map[i], j, scale, value))
                max_change = max(max_change, i - slide_map[i])
            else:
                zooming_frame.append((i, j, scale, value))
        if (board_width2 == self._board_width and
                board_height2 == self._board_height):
            zooming_transform = transform
        else:
            (width, height) = self._get_size_func()
            zooming_transform = _BoardTransform()
            zooming_transform.setup(width,
                                    height,
                                    board_width2,
                                    board_height2)
        frames[_ANIM_STAGE_ZOOM] = (zooming_transform, zooming_frame)
        if max_change > 0 or (zooming_transform is not transform):
            lengths[_ANIM_STAGE_ZOOM] = 4 * _ANIM_SCALE
        else:
            lengths[_ANIM_STAGE_ZOOM] = 0.0

        self._anim_frames = frames
        self._anim_lengths = lengths

    def _recalc_anim_coords(self):
        if not self.board_is_valid():
            self._anim_coords = []
            self._board_transform = _BoardTransform()
            return

        stage = self._anim_stage
        prev_stage = _ANIM_STAGES[_ANIM_STAGES.index(stage, 1) - 1]
        (start_transform, start_coords) = self._anim_frames[prev_stage]
        (end_transform, end_coords) = self._anim_frames[stage]

        length = self.get_anim_length()
        if length == 0.0:
            w = 0.0
        else:
            w = float(min(1.0, max(0.0, self._anim_time / length)))
        inv_w = (1.0 - w)

        if start_coords is end_coords:
            self._anim_coords = start_coords
        else:
            coords = []
            for i in range(len(start_coords)):
                (x1, y1, s1, color1) = start_coords[i]
                (x2, y2, s2, color2) = end_coords[i]
                x = (x1 * inv_w + x2 * w)
                y = (y1 * inv_w + y2 * w)
                s = (s1 * inv_w + s2 * w)
                coords.append((x, y, s, color1))
            self._anim_coords = coords

        if start_transform is end_transform:
            self._board_transform = start_transform
        else:
            self._board_transform = _tween(start_transform, end_transform, w)

    def resize(self, width, height):
        self._recalc_game_anim_frames()
        self._recalc_anim_coords()
        self._invalidate_board()

    def draw(self, cr, width, height):
        # Draws the widget.
        _draw_background(cr, width, height)
        cr.save()
        self._board_transform.set_up_cairo(cr)
        self._animate_board(cr)
        cr.restore()

    def _animate_board(self, cr):
        for (x, y, scale, value) in self._anim_coords:
            if scale > 0.0:
                self._draw_scaled_block(cr, x, y, value, scale)

    def _draw_scaled_block(self, cr, x, y, value, scale):
        c = color.colors[value]
        cr.set_source_rgb(*c)
        inset = 0.5 + scale * (_BLOCK_GAP - 0.5)
        self._draw_square(cr, x, y, -inset)

    def _draw_square(self, cr, x, y, margin):
        # Draws a square in the given grid cell with the given margin.
        x1 = float(x) - margin
        y1 = float(y) - margin
        size = 1.0 + margin * 2
        cr.rectangle(x1, y1, size, size)
        cr.fill()

    def _recalc_board_dimensions(self):
        if self.board_is_valid():
            self._board_width = self._board.width
            self._board_height = self._board.height
        else:
            self._board_width = 1
            self._board_height = 1

    def board_is_valid(self):
        # Returns True if the board is set and has valid dimensions (>=1).
        return (self._board is not None and not self._board.is_empty())


class WinDrawer(object):
    """Object to manage the drawing of the win animation."""

    def __init__(self, get_size_func, invalidate_rect_func, *args, **kwargs):
        super(WinDrawer, self).__init__(*args, **kwargs)

        self._anim_time = 0.0

        self._win_coords = []
        self._win_starts = []
        self._win_ends = []
        self._anim_length = 0
        self._win_size = (0, 0)
        self._win_transform = None
        self._win_color = 0

        (tiles, width, height) = self._get_win_tiles()
        self._win_size = (width, height)

        # Callback functions set by owner.
        self._get_size_func = get_size_func
        self._invalidate_rect_func = invalidate_rect_func

    def set_anim_time(self, t):
        if self._anim_time != t:
            self._anim_time = t
            self._recalc_anim_coords()
            self._invalidate_board()

    def _recalc_anim_coords(self):
        t = max(0.0, min(self._anim_length, self._anim_time))
        coords = []
        for i in range(len(self._win_starts)):
            (s_time, s_x, s_y, s_scale) = self._win_starts[i]
            (e_time, e_x, e_y, e_scale) = self._win_ends[i]
            delta_time = e_time - s_time
            w = max(0.0, min(1.0, (t - s_time) / delta_time))
            inv_w = (1.0 - w)
            x = s_x * inv_w + e_x * w
            y = s_y * inv_w + e_y * w
            scale = s_scale * inv_w + e_scale * w
            coords.append((x, y, scale))
        self._win_coords = coords

    def get_win_color(self):
        return self._win_color

    def set_win_state(self, draw_flag, win_color):
        if draw_flag:
            self.init()
            self._win_color = win_color
            self.set_anim_time(self.get_anim_length())

    def get_anim_length(self):
        """Returns the length of the win animation (in seconds)."""
        return self._anim_length

    def init(self):
        r = random.Random()
        r.seed()
        (tiles, width, height) = self._get_win_tiles()
        tiles = self._reorder_win_tiles(r, tiles, width, height)
        self._win_starts = self._get_win_starts(tiles, width, height)
        self._win_ends = self._get_win_ends(tiles)
        self._anim_length = self._get_win_length(tiles)
        self._win_size = (width, height)
        self._win_color = r.randint(1, 5)
        (width, height) = self._get_size_func()
        self.resize(width, height)

    def _invalidate_board(self):
        (width, height) = self._get_size_func()
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = (0, 0, width, height)
        self._invalidate_rect_func(rect)

    def _get_win_tiles(self):
        # Returns a list of ending tile coordinates making up the smiley face,
        # as well as the width and height in tiles.
        data = [list(x.strip()) for x in _SMILEY.strip().splitlines()]
        height = len(data)
        widths = set([len(x) for x in data])
        assert len(widths) == 1
        width = widths.pop()
        assert width > 0
        assert height > 0
        tiles = []
        for i in range(height):
            for j in range(width):
                if data[i][j] == 'x':
                    # Invert y axis because we use the board tile engine to
                    # display, which uses cartesian coordinates instead of
                    # display coordinates.
                    tiles.append((j, height - i - 1))
        return (tiles, width, height)

    def _reorder_win_tiles(self, r, tiles, width, height):
        # Re-sorts tiles by several randomly chosen criteria.
        def radial(coord):
            (x, y) = coord
            x = float(x) / width - 0.5
            y = float(y) / height - 0.5
            return 2 * math.sqrt(x * x + y * y)

        def x(coord):
            return float(coord[0]) / width

        def y(coord):
            return float(coord[1]) / height

        def angle(coord):
            (x, y) = coord
            x = float(x) / width - 0.5
            y = float(y) / height - 0.5
            angle = math.atan2(y, x)
            return (angle / math.pi + 1) / 2
        funcs = [radial, x, y, angle]
        r.shuffle(funcs)
        invs = [r.choice((-1, 1)), r.choice((-1, 1))]
        pairs = []
        w = r.random()
        for coord in tiles:
            score = funcs[0](coord) * invs[0] + funcs[1](coord) * invs[1] * w
            pairs.append((score, coord))
        pairs.sort()
        # Re-interleave pairs, if desired.
        if r.randint(0, 1):
            index1 = int(len(pairs) // 2)
            list1 = pairs[:index1]
            list2 = pairs[index1:]
            if r.randint(0, 1):
                list2.reverse()
            pairs = _interleave(list1, list2)
        return [pair[1] for pair in pairs]

    def _get_win_starts(self, tiles, width, height):
        # Returns a list of starting coordinates for tiles.
        starts = []
        assert width > 0
        assert height > 0
        start_x = width / 2.0 - 0.5
        start_y = height / 2.0 - 0.5
        for (i, (x, y)) in enumerate(tiles):
            starts.append((i * _ANIM_SCALE, start_x, start_y, 0.0))
            # starts.append((i, x, y, 0.0))
        return starts

    def _get_win_ends(self, tiles):
        # Returns a list of ending coordinates for the tiles in the unit
        # square.
        ends = []
        for (i, (x, y)) in enumerate(tiles):
            ends.append(((i + 8) * _ANIM_SCALE, x, y, 1.0))
        return ends

    def _get_win_length(self, tiles):
        # Returns the length of the win animation for the given set of tiles
        # (in seconds).
        return (len(tiles) + 8) * _ANIM_SCALE

    def resize(self, width, height):
        if self._win_size == (0, 0):
            return
        self._win_transform = _BoardTransform()
        self._win_transform.setup(width,
                                  height,
                                  self._win_size[0],
                                  self._win_size[1])

    def draw(self, cr, width, height):
        # Draws the widget.
        _draw_background(cr, width, height)
        cr.save()
        self._win_transform.set_up_cairo(cr)
        self._draw_win(cr)
        cr.restore()

    def _draw_win(self, cr):
        for (x, y, scale) in self._win_coords:
            if scale > 0.0:
                self._draw_scaled_block(cr, x, y, self._win_color, scale)

    def _draw_scaled_block(self, cr, x, y, value, scale):
        c = color.colors[value]
        cr.set_source_rgb(*c)
        inset = 0.5 + scale * (_BLOCK_GAP - 0.5)
        self._draw_square(cr, x, y, -inset)

    def _draw_square(self, cr, x, y, margin):
        # Draws a square in the given grid cell with the given margin.
        x1 = float(x) - margin
        y1 = float(y) - margin
        size = 1.0 + margin * 2
        cr.rectangle(x1, y1, size, size)
        cr.fill()


def _draw_background(cr, width, height):
    # Draws the board background using the given cairo context and
    # width/height.
    cr.set_source_rgb(*_BG_COLOR)
    cr.rectangle(0, 0, width, height)
    cr.fill()


class _BoardTransform(object):
    # Represents a transformation from board space to screen space.
    def __init__(self):
        self.scale_x = 1
        self.scale_y = 1
        self.offset_x = 0
        self.offset_y = 0
        self.to_center_x = 0
        self.to_center_y = 0
        self.from_center_x = 0
        self.from_center_y = 0

    def set_up_cairo(self, cr):
        cr.translate(self.to_center_x,
                     self.to_center_y)
        cr.scale(self.scale_x,
                 self.scale_y)
        cr.translate(self.from_center_x,
                     self.from_center_y)

    def setup(self, width, height, cells_across, cells_down):
        if cells_across == 0 or cells_down == 0:
            self.scale_x = 1
            self.scale_y = 1
            self.offset_x = 0
            self.offset_y = 0
            return

        border = min(float(width) * _BORDER, float(height) * _BORDER)
        internal_width = width - border * 2
        internal_height = height - border * 2

        scale_x = float(internal_width) / cells_across
        scale_y = float(internal_height) / cells_down

        scale = min(scale_x, scale_y)

        self.scale_x = scale
        self.scale_y = -scale
        self.offset_x = (width - cells_across * scale) / 2
        self.offset_y = height - (height - cells_down * scale) / 2

        self.to_center_x = float(width) / 2
        self.to_center_y = self.offset_y
        self.from_center_x = -float(cells_across) / 2
        self.from_center_y = 0

    def transform(self, x, y):
        x1 = int(float(x) * self.scale_x + self.offset_x)
        y1 = int(float(y) * self.scale_y + self.offset_y)
        return (x1, y1)

    def inverse_transform(self, x, y):
        if self.scale_x == 0 or self.scale_y == 0:
            return (0, 0)
        x1 = int((float(x) - self.offset_x) / self.scale_x)
        y1 = int((float(y) - self.offset_y) / self.scale_y)
        return (x1, y1)


def _tween(trans1, trans2, w):
    t = _BoardTransform()
    inv_w = 1.0 - w
    t.scale_x = trans1.scale_x * inv_w + trans2.scale_x * w
    t.scale_y = trans1.scale_y * inv_w + trans2.scale_y * w
    t.offset_x = trans1.offset_x * inv_w + trans2.offset_x * w
    t.offset_y = trans1.offset_y * inv_w + trans2.offset_y * w
    t.to_center_x = trans1.to_center_x * inv_w + trans2.to_center_x * w
    t.to_center_y = trans1.to_center_y * inv_w + trans2.to_center_y * w
    t.from_center_x = trans1.from_center_x * inv_w + trans2.from_center_x * w
    t.from_center_y = trans1.from_center_y * inv_w + trans2.from_center_y * w
    return t


def _interleave(*args):
    # From Richard Harris' recipe:
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/511480
    for idx in range(0, max(len(arg) for arg in args)):
        for arg in args:
            try:
                yield arg[idx]
            except IndexError:
                continue
