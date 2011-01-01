#!/usr/bin/env python
#
# Copyright (C) 2009, Joseph C. Lee
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

from __future__ import with_statement

from gettext import gettext as _

import cairo
import gobject
import gtk
import math
import os
import rsvg
import time

import board
from anim import Anim
from gridwidget import BoardDrawer, RemovalDrawer, WinDrawer

if 'SUGAR_BUNDLE_PATH' in os.environ:
    from sugar.graphics import style
    _DEFAULT_SPACING = style.DEFAULT_SPACING
    _DEFAULT_PADDING = style.DEFAULT_PADDING
    _BG_COLOR = tuple(style.COLOR_SELECTION_GREY.get_rgba()[:3])
    _TOOLBAR_COLOR = tuple(style.COLOR_TOOLBAR_GREY.get_rgba()[:3])
else:
    # Fallbacks for non-Sugar testing.
    _DEFAULT_SPACING = 15
    _DEFAULT_PADDING = 6
    _BG_COLOR = (0.75, 0.75, 0.75)
    _TOOLBAR_COLOR = (0.16, 0.16, 0.16)

_CURSOR_COLOR = (.8, .8, .8)
_CURSOR_OUTLINE_COLOR = (.4, .4, .4)

# Proportion of the _PreviewWidget's height occupied by emulated button bar.
_ICON_HEIGHT = 0.1

# Proportion of the _PreviewWidget's height to scale the mouse cursor.
_CURSOR_SCALE = 0.12

# Proportion of the _PreviewWidget's cursor width to make the thickness of its
# lines.
_CURSOR_WEIGHT_SCALE = 0.15
_CURSOR_OUTLINE_WEIGHT_SCALE = 0.3

# Proportion of the _PreviewWidget's cursor width to make the mouse click
# animation.
_CLICK_INNER_RADIUS = 0.1
_CLICK_OUTER_RADIUS = 0.7

# Proportion of the _PreviewWidget's cursor width to make the thickness of the
# click animation's lines.
_CLICK_WEIGHT_SCALE = 0.1
_CLICK_OUTLINE_WEIGHT_SCALE = 0.2

# Speed of the click animation, in seconds.
_CLICK_SPEED = 0.2

# Speed of the mouse, in units (4x3 per screen) per second.
_MOUSE_SPEED = 0.5

class HelpWidget(gtk.EventBox):
    def __init__(self, icon_file_func, *args, **kwargs):
        super(HelpWidget, self).__init__(*args, **kwargs)

        vbox = gtk.VBox()
        self.add(vbox)

        self._stages = [
            _HelpStage1(icon_file_func),
            _HelpStage2(icon_file_func),
            _HelpStage3(icon_file_func),
            _HelpStage4(icon_file_func),
            _HelpStage5(icon_file_func),
        ]
        self._stage_index = 0
        self._notebook = gtk.Notebook()
        self._notebook.set_show_tabs(False)
        for stage in self._stages:
            self._notebook.append_page(stage)
        vbox.pack_start(self._notebook)

        self._reset_current_stage()

    def can_prev_stage(self):
        """Returns True if the help widget can move to the previous stage."""
        return (self._stage_index != 0)

    def can_next_stage(self):
        """Returns True if the help widget can move to the next stage."""
        return (self._stage_index < len(self._stages) - 1)

    def prev_stage(self):
        """Moves the help widget to the previous stage."""
        self._stage_index = max(0, self._stage_index - 1)
        self._reset_current_stage()

    def next_stage(self):
        """Moves the help widget to the next stage."""
        self._stage_index = min(len(self._stages) - 1, self._stage_index + 1)
        self._reset_current_stage()

    def replay_stage(self):
        """Replays the current stage."""
        self._stages[self._stage_index].reset()

    def _reload_clicked_cb(self, source):
        self._reset_current_stage()

    def _reset_current_stage(self):
        self._notebook.set_current_page(self._stage_index)
        self._stages[self._stage_index].reset()


class _HelpStage(gtk.EventBox):
    # An abstract parent class for objects that represent an animated help
    # screen widget with a description.
    def __init__(self, icon_file_func, *args, **kwargs):
        super(_HelpStage, self).__init__(*args, **kwargs)

        hbox = gtk.HBox()
        self.add(hbox)

        vbox = gtk.VBox()
        hbox.pack_start(vbox, expand=True, padding=_DEFAULT_SPACING)

        self.preview = _PreviewWidget(icon_file_func)
        vbox.pack_start(self.preview, expand=True, padding=_DEFAULT_PADDING)

        label = gtk.Label(self.get_message())
        label.set_line_wrap(True)
        vbox.pack_start(label, expand=False, padding=_DEFAULT_PADDING)

        self.board = None
        self.undo_stack = []

        self.anim = None
        self._actions = []
        self._action_index = 0

        actions = self._get_actions()
        self._actions = _flatten(actions)

    def get_message(self):
        # Implement to return stage message.
        raise Exception()

    def reset(self):
        # Resets the playback of the animation script.
        self._stop_animation()
        self._action_index = 0
        self.preview.set_cursor_visible(True)
        self.preview.set_click_visible(False)
        self.preview.center_cursor()
        self.next_action()

    def set_board(self, board):
        self.board = board.clone()
        self.preview.board_drawer.set_board(self.board)

    def _stop_animation(self):
        if self.anim:
            self.anim.stop()
            self.anim = None

    def next_action(self):
        # Moves the HelpStage animation script to the next action.
        if self._action_index >= len(self._actions):
            self.preview.set_cursor_visible(False)
            return
        action = self._actions[self._action_index]
        self._action_index += 1
        action(self)

    def _get_actions(self):
        # Implement to return a list stage actions (optionally containing
        # sublists of actions).
        raise Exception()


class _HelpStage1(_HelpStage):
    def __init__(self, *args, **kwargs):
        super(_HelpStage1, self).__init__(*args, **kwargs)

    def get_message(self):
        return _("Goal: Clear the board by removing blocks in groups of 3 or more.")

    def _get_actions(self):
        return [
            _set_board("""..33.
                          .2231
                          12231"""),
            _pause(1),
            _move_to_block(0, 0),
            _pause(0.5),
            _move_to_block(4, 0),
            _pause(0.5),
            _click_to_remove(1, 1),
            _click_to_remove(2, 2),
            _click_to_remove(1, 0, pause=0),
            _show_win(1),
            _pause(1),
        ]


class _HelpStage2(_HelpStage):
    def __init__(self, *args, **kwargs):
        super(_HelpStage2, self).__init__(*args, **kwargs)

    def get_message(self):
        return _("You can't remove groups of one or two blocks.")

    def _get_actions(self):
        return [
            _set_board(""".1..
                          .221
                          1121"""),
            _pause(1),
            _move_to_block(0, 0),
            _pause(1),
            _click(),
            _pause(1),
            _move_to_block(0, 1),
            _move_to_block(1, 2),
            _pause(1),
            _click(),
            _pause(1),
            _move_to_block(2, 2),
            _move_to_block(3, 1),
            _move_to_block(3, 0),
            _pause(1),
            _click(),
            _pause(1),
            _move_to_block(3, 1),
            _move_to_block(2, 2),
            _move_to_block(1, 2),
            _pause(0.5),
            _move_to_block(0, 1),
            _move_to_block(0, 0),
            _move_to_block(1, 0),
            _pause(1),
            _click_to_remove(2, 1),
            _click_to_remove(0, 0, pause=0),
            _show_win(2),
            _pause(1),
        ]


class _HelpStage3(_HelpStage):
    def __init__(self, *args, **kwargs):
        super(_HelpStage3, self).__init__(*args, **kwargs)

    def get_message(self):
        return _("Blocks fall to fill empty gaps, and they slide to fill empty columns.")

    def _get_actions(self):
        return [
            _set_board(""".333.
                          1222.
                          12221
                          32223"""),
            _pause(2),
            _click_to_remove(2, 1),
            _pause(1),
            _click_to_remove(1, 0),
            _click_to_remove(0, 1, pause=0),
            _show_win(3),
            _pause(1),
        ]


class _HelpStage4(_HelpStage):
    def __init__(self, *args, **kwargs):
        super(_HelpStage4, self).__init__(*args, **kwargs)

    def get_message(self):
        return _("If you get stuck, you can undo to try again.")

    def _get_actions(self):
        return [
            _set_board("""1211
                          1221"""),
            _pause(2),
            _click_to_remove(2, 1),
            _click_to_remove(1, 1),
            _move_to_block(0, 1),
            _pause(1),
            _click(),
            _pause(1),
            _click(),
            _pause(2),
            _click_to_undo(),
            _click_to_undo(),
            _click_to_remove(1, 1),
            _click_to_remove(0, 0, pause=0),
            _show_win(4),
            _pause(1),
        ]

def _click_to_remove(x, y, pause=2):
    # Returns an array of action functions to remove the block at (x, y).
    return [
        _move_to_block(x, y),
        _pause(1),
        _click(),
        _remove_piece(x, y),
        _pause(pause),
    ]

def _click_to_undo():
    # Returns an array of action functions to undo the last move.
    return [
        _move_to_icon(2),
        _pause(1),
        _click(),
        _undo(),
    ]


class _HelpStage5(_HelpStage):
    def __init__(self, *args, **kwargs):
        super(_HelpStage5, self).__init__(*args, **kwargs)

    def get_message(self):
        return _("There is always a way to clear the board.")

    def _get_actions(self):
        return [
            # Difficult game seed: 5234
            _set_board("""132.1..1.1...4
                          15244.25.1...4
                          12244114.1..44
                          12254314.1..43
                          15251324.1..11
                          15253413.1..14
                          53251213.5..43
                          53252113.5..33
                          53242114.5..33
                          34232114.1..32
                          34115113.51111
                          54131215452221
                          24231423423222
                          24245323423224
                          24245423423244"""),
            _click_to_remove(12, 9),
            _click_to_remove(12, 9),
            _click_to_remove(2, 12),
            _click_to_remove(1, 11),
            _click_to_remove(3, 4),
            _click_to_remove(3, 3),
            _click_to_remove(3, 2),
            _click_to_remove(1, 3),
            _click_to_remove(1, 3),
            _click_to_remove(1, 2),
            _click_to_remove(5, 9),
            _click_to_remove(2, 6),
            _click_to_remove(3, 6),
            _click_to_undo(),
            _click_to_undo(),
            _click_to_remove(3, 7),
            _click_to_remove(2, 7),
            _click_to_remove(3, 6),
            _click_to_remove(6, 1),
            _click_to_remove(6, 4),
            _click_to_remove(5, 4),
            _click_to_remove(6, 4),
            _click_to_remove(6, 3),
            _click_to_remove(2, 5),
            _click_to_remove(3, 4),
            _click_to_remove(4, 3),
            _click_to_remove(1, 4),
            _click_to_undo(),
            _click_to_remove(2, 5),
            _click_to_remove(1, 4),
            _click_to_remove(1, 2),
            _click_to_remove(1, 2),
            _click_to_remove(1, 1),
            _click_to_remove(1, 1),
            _click_to_remove(1, 1),
            _click_to_remove(1, 1),
            _click_to_remove(1, 0),
            _click_to_remove(0, 0, pause=0),
            _show_win(5),
            _pause(1),
        ]

# The following are functions that return a function that, given a HelpStage
# object will set it up to perform the appropriate action.

def _set_board(board_string):
    # Returns a function to reset the game board to a given state.
    board = _make_board(board_string)
    def action(stage):
        stage.set_board(board)
        stage.undo_stack = []
        stage.preview.set_drawer(stage.preview.board_drawer)
        stage.next_action()
    return action

def _pause(delay):
    # Returns a function to delay playback by the given amount of time.
    def action(stage):
        start_time = time.time()
        def update_func():
            delta = time.time() - start_time
            return delta < delay
        def end_anim_func(anim_stopped):
            if not anim_stopped:
                stage.next_action()
        stage.anim = Anim(update_func, end_anim_func)
        stage.anim.start()
    return action

def _move_to_block(x, y):
    # Returns a function to move the mouse cursor to the given block coordinate.
    def coord_func(stage):
        return stage.preview.get_block_coord(x, y)
    return _move_to(coord_func)

def _move_to_icon(index):
    # Returns a function to move the mouse cursor to the given icon.
    def coord_func(stage):
        return stage.preview.get_icon_coord(index)
    return _move_to(coord_func)

def _move_to(coord_func):
    def action(stage):
        # Caveat: This has the potential to get a little messed up if it is an
        # early action in a stage or if the screen changes size as the cursor
        # is moving...  Best to keep a pause before it in the sequence.
        (old_x, old_y) = stage.preview.get_cursor_pos()
        (new_x, new_y) = coord_func(stage)
        delta_x = new_x - old_x
        delta_y = new_y - old_y
        dist = math.sqrt(delta_x * delta_x + delta_y * delta_y)
        move_time = dist * _MOUSE_SPEED
        start_time = time.time()
        def update_func():
            delta = time.time() - start_time
            if delta >= move_time or move_time == 0.0:
                return False
            t = max(0.0, min(1.0, delta / move_time))
            # Use the first half of cosine wave to ease in/out.
            w = 1.0 - (0.5 * math.cos(t * math.pi) + 0.5)
            inv_w = 1.0 - w
            move_x = old_x * inv_w + new_x * w
            move_y = old_y * inv_w + new_y * w
            stage.preview.set_cursor_pos(move_x, move_y)
            return True
        def end_anim_func(anim_stopped):
            if not anim_stopped:
                stage.next_action()
        stage.anim = Anim(update_func, end_anim_func)
        stage.anim.start()
    return action

def _click():
    # Returns a function to play the mouse-click animation.
    def action(stage):
        start_time = time.time()
        stage.preview.set_click_visible(True)
        def update_func():
            delta = time.time() - start_time
            return (delta < _CLICK_SPEED)
        def end_anim_func(anim_stopped):
            stage.preview.set_click_visible(False)
            if not anim_stopped:
                stage.next_action()
        stage.anim = Anim(update_func, end_anim_func)
        stage.anim.start()
    return action

def _remove_piece(x, y):
    # Returns a function to animate the removal of the given piece.
    def action(stage):
        contiguous = stage.board.get_contiguous(x, y)
        removal_drawer = stage.preview.removal_drawer
        stage.preview.set_drawer(removal_drawer)
        removal_drawer.init(stage.board, contiguous)
        removal_drawer.set_anim_time(0.0)
        start_time = time.time()

        def update_func(start_time_ref=[start_time]):
            delta = time.time() - start_time_ref[0]
            length = removal_drawer.get_anim_length()
            if delta > length:
                if not removal_drawer.next_stage():
                    return False
                start_time_ref[0] = time.time()
                delta = 0.0
            removal_drawer.set_anim_time(delta)
            return True

        def local_end_anim_func(anim_stopped):
            stage.preview.set_drawer(stage.preview.board_drawer)
            stage.undo_stack.append(stage.board)
            board = stage.board.clone()
            board.clear_pieces(contiguous)
            board.drop_pieces()
            board.remove_empty_columns()
            stage.set_board(board)
            if not anim_stopped:
                stage.next_action()
        stage.anim = Anim(update_func, local_end_anim_func)
        stage.anim.start()
    return action

def _show_win(color):
    # Returns a function to animate a win.
    def action(stage):
        win_drawer = stage.preview.win_drawer
        stage.preview.set_drawer(win_drawer)
        win_drawer.set_win_state(True, color)
        length = win_drawer.get_anim_length()
        start_time = time.time()

        def update_func():
            delta = time.time() - start_time
            win_drawer.set_anim_time(min(delta, length))
            return (delta <= length)

        def local_end_anim_func(anim_stopped):
            win_drawer.set_anim_time(length)
            if not anim_stopped:
                stage.next_action()

        stage.anim = Anim(update_func, local_end_anim_func)
        stage.anim.start()
    return action

def _undo():
    # Returns a function that undoes the previous move.
    def action(stage):
        board = stage.undo_stack.pop()
        stage.set_board(board)
        stage.next_action()
    return action

class _PreviewWidget(gtk.DrawingArea):
    __gsignals__ = {
        'expose-event': 'override',
        'size-allocate': 'override',
    }

    def __init__(self, icon_file_func, *args, **kwargs):
        super(_PreviewWidget, self).__init__(*args, **kwargs)

        self.board_drawer = \
            BoardDrawer(get_size_func=self._get_drawer_size,
                        invalidate_rect_func=self._invalidate_drawer_rect)
        self.removal_drawer = \
            RemovalDrawer(get_size_func=self._get_drawer_size,
                          invalidate_rect_func=self._invalidate_drawer_rect)
        self.win_drawer = \
            WinDrawer(get_size_func=self._get_drawer_size,
                      invalidate_rect_func=self._invalidate_drawer_rect)

        self._icon_file_func = icon_file_func

        self._preview_rect = gtk.gdk.Rectangle(0, 0, 0, 0)
        self._toolbar_rect = gtk.gdk.Rectangle(0, 0, 0, 0)
        self._drawer_rect = gtk.gdk.Rectangle(0, 0, 0, 0)

        self._drawer = self.board_drawer

        # Mouse position as a floating point value over the 4x3 unit preview
        # area.
        self._cursor_pos = (0.0, 0.0)

        # Cursor size in pixels.
        self._cursor_size = (0, 0)

        self._click_visible = False
        self._cursor_visible = False

    def _get_drawer_size(self):
        return (self._drawer_rect.width, self._drawer_rect.height)

    def _invalidate_drawer_rect(self, rect):
        if self.window:
            (x, y) = (self._drawer_rect.x, self._drawer_rect.y)
            offset_rect = gtk.gdk.Rectangle(rect.x + x,
                                            rect.y + y,
                                            rect.width,
                                            rect.height)
            self.window.invalidate_rect(offset_rect, True)

    def set_drawer(self, drawer):
        self._drawer = drawer
        r = self._preview_rect
        self._invalidate_client_rect(0, 0, r.width, r.height)

    def center_cursor(self):
        self.set_cursor_pos(2.0, 1.5)

    def set_cursor_pos(self, x, y):
        self._invalidate_cursor()
        self._cursor_pos = (x, y)
        self._invalidate_cursor()
        self._update_mouse_position()

    def get_cursor_pos(self):
        return self._cursor_pos

    def set_click_visible(self, click_visible):
        self._click_visible = click_visible
        self._invalidate_click()

    def set_cursor_visible(self, cursor_visible):
        self._cursor_visible = cursor_visible
        self._invalidate_cursor()

    def get_block_coord(self, x, y):
        # Returns the coordinate of the given board block in terms of 4x3 units.
        if (self._preview_rect.width == 0
            or self._preview_rect.height == 0):
            return (0, 0)
        (drawer_x, drawer_y) = self.board_drawer.get_block_coord(x, y)
        preview_x = drawer_x
        preview_y = drawer_y + self._toolbar_rect.height
        out_x = preview_x * 4.0 / self._preview_rect.width
        out_y = preview_y * 3.0 / self._preview_rect.height
        return (out_x, out_y)

    def get_icon_coord(self, index):
        # Returns the coordinate of the given icon in terms of 4x3 units.
        icon_height = self._toolbar_rect.height
        preview_x = icon_height * (index + 0.5)
        preview_y = icon_height * 0.5
        out_x = preview_x * 4.0 / self._preview_rect.width
        out_y = preview_y * 3.0 / self._preview_rect.height
        return (out_x, out_y)

    def _get_cursor_pixel_coords(self):
        (x, y) = self._cursor_pos
        pixel_x = x * self._preview_rect.width / 4
        pixel_y = y * self._preview_rect.height / 3
        return (pixel_x, pixel_y)

    def _invalidate_cursor(self):
        (pixel_x, pixel_y) = self._get_cursor_pixel_coords()
        self._invalidate_client_rect(pixel_x, pixel_y, *self._cursor_size)

        if self._click_visible:
            self._invalidate_click()

    def _invalidate_click(self):
        (pixel_x, pixel_y) = self._get_cursor_pixel_coords()
        r = self._cursor_size[0] * _CLICK_OUTER_RADIUS
        r2 = r * 2
        self._invalidate_client_rect(pixel_x - r, pixel_y - r, r2, r2)

    def _invalidate_client_rect(self, x, y, width, height):
        if self.window:
            rect = gtk.gdk.Rectangle(
                int(math.floor(x)) + self._preview_rect.x,
                int(math.floor(y)) + self._preview_rect.y,
                int(math.ceil(width)) + 1,
                int(math.ceil(height)) + 1)
            self.window.invalidate_rect(rect, True)

    def _update_mouse_position(self):
        (pixel_x, pixel_y) = self._get_cursor_pixel_coords()
        (x, y) = (pixel_x, pixel_y - self._toolbar_rect.height)
        self.board_drawer.set_mouse_selection(x, y)

    def do_expose_event(self, event):
        cr = self.window.cairo_create()
        cr.rectangle(event.area.x,
                     event.area.y,
                     event.area.width,
                     event.area.height)
        cr.clip()
        (width, height) = self.window.get_size()
        self._draw(cr, width, height)

    def _draw(self, cr, width, height):
        cr.set_source_rgb(*_BG_COLOR)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        cr.save()
        cr.rectangle(self._preview_rect.x,
                     self._preview_rect.y,
                     self._preview_rect.width,
                     self._preview_rect.height)
        cr.clip()

        self._draw_toolbar(cr)
        self._draw_grid(cr)
        if self._click_visible:
            self._draw_click(cr)
        if self._cursor_visible:
            self._draw_cursor(cr)

        cr.restore()

    def _draw_toolbar(self, cr):
        cr.set_source_rgb(*_TOOLBAR_COLOR)
        cr.rectangle(self._toolbar_rect.x,
                     self._toolbar_rect.y,
                     self._toolbar_rect.width,
                     self._toolbar_rect.height)
        cr.fill()

        icon_height = self._toolbar_rect.height
        scale = icon_height / 55.0
        for (i, icon_name) in enumerate(['new-game',
                                         'replay-game',
                                         'edit-undo',
                                         'edit-redo']):
            file_path = self._icon_file_func(icon_name)
            handle = _get_icon_handle(file_path)
            cr.save()
            cr.translate(self._toolbar_rect.x + i * icon_height,
                         self._toolbar_rect.y)
            cr.scale(scale, scale)
            handle.render_cairo(cr)
            cr.restore()

    def _draw_grid(self, cr):
        cr.save()
        cr.translate(self._drawer_rect.x, self._drawer_rect.y)
        self._drawer.draw(cr, self._drawer_rect.width, self._drawer_rect.height)
        cr.restore()

    def _draw_click(self, cr):
        width = self._cursor_size[0]
        weight = width * _CLICK_WEIGHT_SCALE
        outline_weight = width * _CLICK_OUTLINE_WEIGHT_SCALE
        r1 = width * _CLICK_INNER_RADIUS + outline_weight
        r2 = width * _CLICK_OUTER_RADIUS - outline_weight
        (pixel_x, pixel_y) = self._get_cursor_pixel_coords()
        x = pixel_x + self._preview_rect.x
        y = pixel_y + self._preview_rect.y

        cr.save()
        cr.translate(x, y)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        angle_inc = math.pi * 2.0 / 6
        cr.rotate(angle_inc * 0.75)
        for i in range(6):
            cr.set_line_width(outline_weight)
            cr.set_source_rgb(*_CURSOR_OUTLINE_COLOR)
            cr.move_to(r1, 0)
            cr.line_to(r2, 0)
            cr.stroke()

            cr.set_line_width(weight)
            cr.set_source_rgb(*_CURSOR_COLOR)
            cr.move_to(r1, 0)
            cr.line_to(r2, 0)
            cr.stroke()

            cr.rotate(angle_inc)

        cr.restore()

    def _draw_cursor(self, cr):
        (pixel_x, pixel_y) = self._get_cursor_pixel_coords()
        x = pixel_x + self._preview_rect.x
        y = pixel_y + self._preview_rect.y
        (width, height) = self._cursor_size
        weight = width * _CURSOR_WEIGHT_SCALE
        outline_weight = width * _CURSOR_OUTLINE_WEIGHT_SCALE
        hw = outline_weight / 2.0

        def draw_arrow():
            cr.move_to(x + width * 0.9 - hw, y + hw)
            cr.line_to(x + hw, y + hw)
            cr.line_to(x + hw, y + height * 0.9 - hw)
            cr.move_to(x + hw, y + hw)
            cr.line_to(x + width - hw, y + height - hw)
            cr.stroke()

        cr.save()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        cr.set_line_width(outline_weight)
        cr.set_source_rgb(*_CURSOR_OUTLINE_COLOR)
        draw_arrow()

        cr.set_line_width(weight)
        cr.set_source_rgb(*_CURSOR_COLOR)
        draw_arrow()

        cr.restore()

    def do_size_allocate(self, allocation):
        super(_PreviewWidget, self).do_size_allocate(self, allocation)
        (width, height) = (allocation.width, allocation.height)

        avail_width = width - _DEFAULT_SPACING * 2
        other_height = avail_width * 3 / 4

        avail_height = height - _DEFAULT_SPACING * 2
        other_width = avail_height * 4 / 3

        if other_height < avail_height:
            actual_width = avail_width
            actual_height = other_height
        else:
            actual_width = other_width
            actual_height = avail_height

        icon_height = int(math.ceil(actual_height * _ICON_HEIGHT))
        board_height = actual_height - icon_height

        x_offset = (width - actual_width) / 2
        y_offset = (height - actual_height) / 2

        old_width = self._preview_rect.width
        old_height = self._preview_rect.height

        self._preview_rect = gtk.gdk.Rectangle(x_offset,
                                               y_offset,
                                               actual_width,
                                               actual_height)
        self._toolbar_rect = gtk.gdk.Rectangle(x_offset,
                                               y_offset,
                                               actual_width,
                                               icon_height)
        self._drawer_rect = gtk.gdk.Rectangle(x_offset,
                                              y_offset + icon_height,
                                              actual_width,
                                              board_height)
        self.board_drawer.resize(actual_width, board_height)
        self.removal_drawer.resize(actual_width, board_height)
        self.win_drawer.resize(actual_width, board_height)

        cursor_width = actual_height * _CURSOR_SCALE
        self._cursor_size = (cursor_width, cursor_width)

        self._update_mouse_position()


def _make_board(board_string):
    # Given a string with numbers representing colors, periods representing
    # spaces, and lines separated by whitespace, returns a board object.
    b = board.Board()
    lines = [x.strip() for x in board_string.strip().split()]

    val_map = dict([('.', None)] + [(str(i), i) for i in range(1, 10)])

    for (i, line) in enumerate(reversed(lines)):
        for (j, ch) in enumerate(line):
            b.set_value(j, i, val_map[ch])

    return b

def _flatten(items):
    # Returns a flattened list of items.
    out = []
    for item in items:
        if isinstance(item, list):
            out.extend(_flatten(item))
        else:
            out.append(item)
    return out

# Simple caching mechanism for getting rsvg rendering handles for icons.  (The
# sugar.graphics.icon package doesn't seem to provide an easy way to get at
# them, so we do a little reimplementing here).
_icon_handles = {}

def _get_icon_handle(file_path):
    global _icon_handles

    if file_path not in _icon_handles:
        with open(file_path, 'r') as f:
            data = f.read()
        _icon_handles[file_path] = rsvg.Handle(data=data)

    return _icon_handles[file_path]
