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
_logger = logging.getLogger('implode-activity.gridwidget')

import cairo
import gobject
import gtk
import math
import random

import color

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

_KEY_MAP = {
    gtk.keysyms.KP_Up        : 'up',
    gtk.keysyms.KP_Down      : 'down',
    gtk.keysyms.KP_Left      : 'left',
    gtk.keysyms.KP_Right     : 'right',

    gtk.keysyms.Up           : 'up',
    gtk.keysyms.Down         : 'down',
    gtk.keysyms.Left         : 'left',
    gtk.keysyms.Right        : 'right',

    gtk.keysyms.uparrow      : 'up',
    gtk.keysyms.downarrow    : 'down',
    gtk.keysyms.leftarrow    : 'left',
    gtk.keysyms.rightarrow   : 'right',

    gtk.keysyms.Return       : 'select',
    gtk.keysyms.KP_Space     : 'select',
    gtk.keysyms.KP_Enter     : 'select',
    gtk.keysyms.space        : 'select',
    gtk.keysyms.End          : 'select',
    gtk.keysyms.KP_End       : 'select',

    gtk.keysyms.Home         : 'new',
    gtk.keysyms.KP_Home      : 'new',
    gtk.keysyms.Page_Down    : 'redo',
    gtk.keysyms.KP_Page_Down : 'redo',
    gtk.keysyms.Page_Up      : 'undo',
    gtk.keysyms.KP_Page_Up   : 'undo',
}


# Animation modes.
ANIMATE_NONE = 0
ANIMATE_SHRINK = 1
ANIMATE_FALL = 2
ANIMATE_SLIDE = 3
ANIMATE_ZOOM = 4
ANIMATE_WIN = 5

#import traceback
#def _log_errors(func):
#    # A function decorator to add error logging to selected functions.
#    # (For when GTK eats exceptions).
#    def wrapper(*args, **kwargs):
#        try:
#            return func(*args, **kwargs)
#        except:
#            _logger.debug(traceback.format_exc())
#            raise
#    return wrapper
def _log_errors(func):
    return func

class GridWidget(gtk.DrawingArea):
    """Gtk widget for rendering the game board."""

    __gsignals__ = {
        'piece-selected'  : (gobject.SIGNAL_RUN_LAST, None, (int, int)),
        'undo-key-pressed': (gobject.SIGNAL_RUN_LAST, None, (int,)),
        'redo-key-pressed': (gobject.SIGNAL_RUN_LAST, None, (int,)),
        'new-key-pressed' : (gobject.SIGNAL_RUN_LAST, None, (int,)),
        'button-press-event': 'override',
        'key-press-event': 'override',
        'expose-event': 'override',
        'size-allocate': 'override',
        'motion-notify-event': 'override',
    }

    def __init__(self, *args, **kwargs):
        super(GridWidget, self).__init__(*args, **kwargs)
        self.set_events(gtk.gdk.BUTTON_PRESS_MASK
                        | gtk.gdk.POINTER_MOTION_MASK
                        | gtk.gdk.KEY_PRESS_MASK)
        self.set_flags(gtk.CAN_FOCUS)
        self._board = None
        self._board_width = 0
        self._board_height = 0
        self._removal_block_set = set()
        self._animation_percent = 0.0
        self._animation_mode = ANIMATE_NONE
        self._selected_cell = None
        self._contiguous_map = {}

        # Game animation variables.
        self._animation_coords = []
        self._animation_frames = {}
        self._animation_lengths = {}

        # Winning animation variables.
        self._win_coords = []
        self._win_starts = []
        self._win_ends = []
        self._win_length = 0
        self._win_size = (0,0)
        self._win_transform = None
        self._win_draw_flag = False
        self._win_color = 0

        # Drawing offset and scale.
        self._board_transform = None

    def set_board(self, value):
        self._board = value
        self._recalc_board_dimensions()
        self._recalc_contiguous_map()
        self._init_board_layout(self.allocation.width,
                                self.allocation.height)
        if self._selected_cell is not None:
            # If a cell is selected, clamp it to new board boundaries.
            (x, y) = self._selected_cell
            x = max(0, min(self._board_width  - 1, x))
            y = max(0, min(self._board_height - 1, y))
            self._selected_cell = (x, y)
        self._invalidate_board()

    def set_removal_block_set(self, value):
        self._removal_block_set = value
        self._recalc_game_animation_frames()

    def set_animation_mode(self, value):
        self._animation_mode = value
        if value == ANIMATE_WIN:
            self._recalc_win_animation_frames()
        self._invalidate_board()

    def set_animation_percent(self, value):
        self._animation_percent = value
        self._recalc_animation_coords()

    def set_win_draw_flag(self, value):
        if self._win_draw_flag != value:
            self._win_draw_flag = value
            self._invalidate_board()

    def get_win_draw_flag(self):
        return self._win_draw_flag

    def get_win_color(self):
        return self._win_color

    def set_win_state(self, draw_flag, win_color):
        self._win_draw_flag = draw_flag
        if draw_flag:
            self._recalc_win_animation_frames()
            self._win_color = win_color
            self._invalidate_board()

    def get_animation_length(self):
        if self._animation_mode == ANIMATE_NONE:
            return 0.0
        if self._animation_mode == ANIMATE_WIN:
            return self._win_length
        else:
            return self._animation_lengths[self._animation_mode]

    def _recalc_contiguous_map(self):
        self._contiguous_map = {}
        if self._board is None:
            return
        all_contiguous = self._board.get_all_contiguous()
        for contiguous in all_contiguous:
            for coord in contiguous:
                self._contiguous_map[coord] = contiguous

    @_log_errors
    def do_button_press_event(self, event):
        # Ignore mouse clicks while animating.
        if self._animation_mode != ANIMATE_NONE:
            return
        self.grab_focus()
        self._set_mouse_selection(event.x, event.y)
        if self._selected_cell is not None:
            self.emit('piece-selected', *self._selected_cell)

    def select_center_cell(self):
        if not self._board_is_valid():
            return
        if self._selected_cell is not None:
            self._invalidate_selection(self._selected_cell)
        self._selected_cell = (int(self._board_width / 2),
                               self._board_height - 1)
        self._invalidate_selection(self._selected_cell)

    @_log_errors
    def do_key_press_event(self, event):
        action = _KEY_MAP.get(event.keyval, None)
        if action == 'new':
            self.emit('new-key-pressed', 0)
            return True
        # Ignore key presses while animating.
        if self._animation_mode != ANIMATE_NONE:
            return False
        if not self._board_is_valid():
            self._selected_cell = None
            return False
        else:
            if self._selected_cell is None:
                self.select_center_cell()
                return True
            else:
                if action == 'select':
                    self.emit('piece-selected', *self._selected_cell)
                    return True
                elif action == 'undo':
                    self.emit('undo-key-pressed', 0)
                    return True
                elif action == 'redo':
                    self.emit('redo-key-pressed', 0)
                    return True
                else:
                    (x, y) = self._selected_cell
                    if action == 'up':
                        y = min(self._board_height - 1, y + 1)
                    elif action == 'down':
                        y = max(0, y - 1)
                    elif action == 'left':
                        x = max(0, x - 1)
                    elif action == 'right':
                        x = min(self._board_width - 1, x + 1)
                    if self._selected_cell != (x, y):
                        self._invalidate_selection(self._selected_cell)
                        self._selected_cell = (x, y)
                        self._invalidate_selection(self._selected_cell)
                        return True
                    else:
                        return False

    @_log_errors
    def do_motion_notify_event(self, event):
        if event.is_hint:
            (x, y, state) = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state
        self._set_mouse_selection(x, y)

    def _set_mouse_selection(self, x, y):
        if not self._board_is_valid():
            self._selected_cell = None
            return
        old_selection = self._selected_cell
        (x1, y1) = self._display_to_cell(x, y)
        if (0 <= x1 < self._board_width and 0 <= y1 < self._board_height):
            self._selected_cell = (x1, y1)
        self._invalidate_selection(old_selection)
        self._invalidate_selection(self._selected_cell)

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
        max_x2 = math.ceil( max(pt1[0], pt2[0])) + 1
        min_y2 = math.floor(min(pt1[1], pt2[1])) - 1
        max_y2 = math.ceil( max(pt1[1], pt2[1])) + 1
        if self.window:
            rect = gtk.gdk.Rectangle(int(min_x2),
                                     int(min_y2),
                                     int(max_x2 - min_x2),
                                     int(max_y2 - min_y2))
            self.window.invalidate_rect(rect, True)

    def _invalidate_board(self):
        if self.window:
            alloc = self.allocation
            rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)

    def _display_to_cell(self, x, y):
        # Converts from display coordinate to a cell coordinate.
        return self._board_transform.inverse_transform(x, y)

    def _cell_to_display(self, x, y):
        # Converts from a cell coordinate to a display coordinate.
        return self._board_transform.transform(x, y)

    def _recalc_win_animation_frames(self):
        r = random.Random()
        r.seed()
        (tiles, width, height) = self._get_win_tiles()
        tiles = self._reorder_win_tiles(r, tiles, width, height)
        self._win_starts = self._get_win_starts(tiles, width, height)
        self._win_ends = self._get_win_ends(tiles)
        self._win_length = self._get_win_length()
        self._win_size = (width, height)
        self._win_color = r.randint(1, 5)
        self._recalc_win_transform(self.allocation.width,
                                   self.allocation.height)

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
            index1 = int(len(pairs) / 2)
            list1 = pairs[:index1]
            list2 = pairs[index1:]
            if r.randint(0, 1):
                list2.reverse()
            pairs = _interleave(list1, list2)
        return [x[1] for x in pairs]

    def _get_win_starts(self, tiles, width, height):
        # Returns a list of starting coordinates for tiles.
        starts = []
        assert width > 0
        assert height > 0
        start_x = width / 2.0 - 0.5
        start_y = height / 2.0 - 0.5
        for (i, (x, y)) in enumerate(tiles):
            starts.append((i, start_x, start_y, 0.0))
            #starts.append((i, x, y, 0.0))
        return starts

    def _get_win_ends(self, tiles):
        # Returns a list of ending coordinates for the tiles in the unit
        # square.
        ends = []
        for (i, (x, y)) in enumerate(tiles):
            ends.append((i + 8, x, y, 1.0))
        return ends

    def _get_win_length(self):
        # Returns the length of the win animation based on the existing
        # values for start and end (in "ticks").
        return (len(self._win_starts) + 8)

    def _recalc_game_animation_frames(self):
        if not self._board_is_valid():
            self._animation_frames = {}
            return

        frames = {}
        value_map = self._board.get_value_map()
        lengths = {}

        # Calculate starting coords.
        starting_frame = []
        for ((i, j), value) in value_map.items():
            starting_frame.append((i, j, 1.0, value))
        frames[ANIMATE_NONE] = (self._board_transform, starting_frame)
        lengths[ANIMATE_NONE] = 0.0

        # Calculate shrinking coords.
        shrinking_frame = []
        for (i, j, scale, value) in starting_frame:
            if (i, j) in self._removal_block_set:
                shrinking_frame.append((i, j, 0.0, value))
            else:
                shrinking_frame.append((i, j, scale, value))
        frames[ANIMATE_SHRINK] = (self._board_transform, shrinking_frame)
        if len(self._removal_block_set) > 0:
            lengths[ANIMATE_SHRINK] = 1.0
        else:
            lengths[ANIMATE_SHRINK] = 0.0

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
        frames[ANIMATE_FALL] = (self._board_transform, falling_frame)
        if max_change > 0:
            lengths[ANIMATE_FALL] = 1.0
        else:
            lengths[ANIMATE_FALL] = 0.0

        # Calculate sliding coords.
        sliding_frame = []
        board2.drop_pieces()
        slide_map = board2.get_slide_map()
        max_change = 0
        for(i, j, scale, value) in falling_frame:
            if i in slide_map:
                sliding_frame.append((slide_map[i], j, scale, value))
                max_change = max(max_change, i - slide_map[i])
            else:
                sliding_frame.append((i, j, scale, value))
        frames[ANIMATE_SLIDE] = (self._board_transform, sliding_frame)
        if max_change > 0:
            lengths[ANIMATE_SLIDE] = 1.0
        else:
            lengths[ANIMATE_SLIDE] = 0.0

        # Calculate zooming coords.
        zooming_frame = sliding_frame
        board2.remove_empty_columns()
        board_width2  = board2.width
        board_height2 = board2.height
        if (board_width2 == self._board_width
            and board_height2 == self._board_height):
            zooming_transform = self._board_transform
            lengths[ANIMATE_ZOOM] = 0.0
        else:
            (width, height) = self.window.get_size()
            zooming_transform = _BoardTransform()
            zooming_transform.setup(width,
                                    height,
                                    board_width2,
                                    board_height2)
            lengths[ANIMATE_ZOOM] = 1.0
        frames[ANIMATE_ZOOM] = (zooming_transform, zooming_frame)

        self._animation_frames = frames
        self._animation_lengths = lengths

    def _recalc_animation_coords(self):
        if self._animation_mode == ANIMATE_WIN:
            self._recalc_win_animation_coords()
            self._invalidate_board() # XXX Limit to win animation?
        elif self._animation_mode == ANIMATE_NONE or not self._board_is_valid():
            self._animation_coords = []
        else:
            self._recalc_game_animation_coords()
            self._invalidate_board()

    def _recalc_win_animation_coords(self):
        clamped_percent = max(0.0, min(1.0, self._animation_percent))
        t = clamped_percent * self._win_length
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

    def _recalc_game_animation_coords(self):
        modes = [ANIMATE_NONE,
                 ANIMATE_SHRINK,
                 ANIMATE_FALL,
                 ANIMATE_SLIDE,
                 ANIMATE_ZOOM]
        mode = self._animation_mode
        prev_mode = modes[modes.index(mode, 1) - 1]

        w = float(min(max(self._animation_percent, 0.0), 1.0))
        inv_w = (1.0 - w)
        (start_transform, start_coords) = self._animation_frames[prev_mode]
        (end_transform,   end_coords  ) = self._animation_frames[mode]

        if start_coords is end_coords:
            self._animation_coords = start_coords
        else:
            coords = []
            for i in range(len(start_coords)):
                (x1, y1, s1, color1) = start_coords[i]
                (x2, y2, s2, color2) = end_coords[i]
                x = (x1 * inv_w + x2 * w)
                y = (y1 * inv_w + y2 * w)
                s = (s1 * inv_w + s2 * w)
                coords.append((x, y, s, color1))
            self._animation_coords = coords

        if start_transform is end_transform:
            self._board_transform = start_transform
        else:
            self._board_transform.tween(start_transform, end_transform, w)

    @_log_errors
    def do_expose_event(self, event):
        cr = self.window.cairo_create()
        cr.rectangle(event.area.x,
                     event.area.y,
                     event.area.width,
                     event.area.height)
        cr.clip()
        (width, height) = self.window.get_size()
        self._draw(cr, width, height)

    @_log_errors
    def do_size_allocate(self, allocation):
        super(GridWidget, self).do_size_allocate(self, allocation)
        self._init_board_layout(allocation.width, allocation.height)

    def _init_board_layout(self, width, height):
        if not self._board_is_valid():
            self._board_transform = _BoardTransform()
        else:
            self._board_transform = _BoardTransform()
            self._board_transform.setup(width,
                                       height,
                                       self._board_width,
                                       self._board_height)
        self._recalc_win_transform(width, height)

    def _recalc_win_transform(self, width, height):
        if self._win_size == (0, 0):
            return
        self._win_transform = _BoardTransform()
        self._win_transform.setup(width,
                                  height, 
                                  self._win_size[0],
                                  self._win_size[1])

    def _draw(self, cr, width, height):
        # Draws the widget.

        cr.set_source_rgb(*_BG_COLOR)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        cr.save()
        self._board_transform.set_up_cairo(cr)
        if self._animation_mode == ANIMATE_NONE:
            self._draw_board(cr)
        elif self._animation_mode in (ANIMATE_SHRINK,
                                      ANIMATE_FALL,
                                      ANIMATE_SLIDE,
                                      ANIMATE_ZOOM):
            self._animate_board(cr)
        cr.restore()

        if self._win_draw_flag:
            cr.save()
            self._win_transform.set_up_cairo(cr)
            self._draw_win(cr)
            cr.restore()
        elif self._animation_mode == ANIMATE_WIN:
            cr.save()
            self._win_transform.set_up_cairo(cr)
            self._draw_animated_win(cr)
            cr.restore()

    def _animate_board(self, cr):
        self._animate_blocks(cr)

    def _draw_board(self, cr):
        # Draws the game board on the widget, where each unit corresponds to
        # a cell on the board.
        self._draw_blocks(cr)
        self._draw_selected(cr)
        self._draw_selected_dot(cr)

    def _draw_win(self, cr):
        for (time, x, y, scale) in self._win_ends:
            if scale > 0.0:
                self._draw_scaled_block(cr, x, y, self._win_color, scale)

    def _draw_animated_win(self, cr):
        value = 1
        for (x, y, scale) in self._win_coords:
            if scale > 0.0:
                self._draw_scaled_block(cr, x, y, self._win_color, scale)

    def _animate_blocks(self, cr):
        for (x, y, scale, value) in self._animation_coords:
            if scale > 0.0:
                self._draw_scaled_block(cr, x, y, value, scale)

    def _draw_blocks(self, cr):
        if not self._board_is_valid():
            return

        value_map = self._board.get_value_map()
        for (coord, value) in value_map.items():
            self._draw_block(cr, coord[0], coord[1], value)

    def _draw_selected(self, cr):
        # Draws a white background to selected blocks, then redraws blocks
        # on top.
        if (self._selected_cell is None
            or self._selected_cell not in self._contiguous_map):
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

    def _draw_selected_dot(self, cr):
        if self._selected_cell is None:
            return
        # Draws a dot indicating the selected cell.
        cr.set_source_rgb(*_SELECTED_COLOR)

        (x, y) = self._selected_cell
        cr.arc(x + 0.5, y + 0.5, _SELECTED_DOT_RADIUS, 0, math.pi * 2.0)
        cr.fill()

    def _recalc_board_dimensions(self):
        if self._board_is_valid():
            self._board_width  = self._board.width
            self._board_height = self._board.height
        else:
            self._board_width  = 1
            self._board_height = 1

    def _board_is_valid(self):
        # Returns True if the board is set and has valid dimensions (>=1).
        return (self._board is not None
                and not self._board.is_empty())

class _BoardTransform(object):
    def __init__(self):
        self.scale_x = 1
        self.scale_y = 1
        self.offset_x = 0
        self.offset_y = 0

    def set_up_cairo(self, cr):
        cr.translate(self.offset_x,
                     self.offset_y)
        cr.scale(self.scale_x,
                 self.scale_y)

    def tween(self, trans1, trans2, w):
        inv_w = 1.0 - w
        self.scale_x  = trans1.scale_x  * inv_w + trans2.scale_x  * w
        self.scale_y  = trans1.scale_y  * inv_w + trans2.scale_y  * w
        self.offset_x = trans1.offset_x * inv_w + trans2.offset_x * w
        self.offset_y = trans1.offset_y * inv_w + trans2.offset_y * w

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
        self.offset_x =          (width - cells_across * scale) / 2
        self.offset_y = height - (height - cells_down * scale) / 2

    def transform(self, x, y):
        x1 = int(float(x) * self.scale_x + self.offset_x)
        y1 = int(float(y) * self.scale_y + self.offset_y)
        return (x1, y1)

    def inverse_transform(self, x, y):
        x1 = int((float(x) - self.offset_x) / self.scale_x)
        y1 = int((float(y) - self.offset_y) / self.scale_y)
        return (x1, y1)

def _interleave(*args):
    # From Richard Harris' recipe:
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/511480
    for idx in range(0, max(len(arg) for arg in args)):
        for arg in args:
            try:
                yield arg[idx]
            except IndexError:
                continue
