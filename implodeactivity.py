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
_logger = logging.getLogger('implode-activity')

from gettext import gettext as _

from sugar3.activity.activity import Activity, get_bundle_path
from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.graphics.toolbutton import ToolButton

from sugar3.activity.widgets import ActivityToolbarButton, StopButton
from sugar3.graphics.toolbarbox import ToolbarBox, ToolbarButton

from implodegame import ImplodeGame
from helpwidget import HelpWidget

import os

import json
from StringIO import StringIO
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gdk

from keymap import KEY_MAP

class ImplodeActivity(Activity):
    def __init__(self, handle):
        super(ImplodeActivity, self).__init__(handle)

        _logger.debug('Starting implode activity...')

        self.max_participants = 1

        self._game = ImplodeGame()

        game_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        game_box.pack_start(self._game, True, True, 0)
        self._stuck_strip = _StuckStrip()

        self._configure_toolbars()

        self.set_canvas(game_box)

        # Show everything except the stuck strip.
        self.show_all()
        game_box.pack_end(self._stuck_strip, expand=False, fill=False, padding=0)

        self._game.connect('show-stuck', self._show_stuck_cb)
        self._stuck_strip.connect('undo-clicked', self._stuck_undo_cb)
        game_box.connect('key-press-event', self._key_press_event_cb)

        self._game.grab_focus()

        last_game_path = self._get_last_game_path()
        if os.path.exists(last_game_path):
            self.read_file(last_game_path)

    def _get_last_game_path(self):
        return os.path.join(self.get_activity_root(), 'data', 'last_game')

    def read_file(self, file_path):
        # Loads the game state from a file.
        f = file(file_path, 'rt')
        content = f.read()
        io = StringIO(content)
        file_data = json.load(io)
        f.close()

        # print file_data
        # _logger.debug(file_data)
        (file_type, version, game_data) = file_data
        if file_type == 'Implode save game' and version <= [1, 0]:
            self._game.set_game_state(game_data)
            # Ensure that the visual display matches the game state. <MS>
            self._levels_buttons[game_data['difficulty']].props.active = True

    def write_file(self, file_path):
        # Writes the game state to a file.
        game_data = self._game.get_game_state()
        file_data = ['Implode save game', [1, 0], game_data]
        last_game_path = self._get_last_game_path()
        for path in (file_path, last_game_path):
            f = file(path, 'wt')
            io = StringIO()
            json.dump(file_data,io)
            content = io.getvalue()
            f.write(content)
            f.close()

    def _show_stuck_cb(self, state, data=None):
        if data:
            self._stuck_strip.show_all()
        else:
            if self._stuck_strip.get_focus_child():
                self._game.grab_focus()
            self._stuck_strip.hide()

    def _stuck_undo_cb(self, state, data=None):
        self._game.undo_to_solvable_state()

    def _key_press_event_cb(self, source, event):
        # Make the game navigable by keypad controls.
        action = KEY_MAP.get(event.keyval, None)
        if action is None:
            return False
        if not self._stuck_strip.get_state_flags() & Gtk.AccelFlags.VISIBLE:
            return True
        if self._game.get_focus_child():
            if action == 'down':
                self._stuck_strip.button.grab_focus()
            return True
        elif self._stuck_strip.get_focus_child():
            if action == 'up':
                self._game.grab_focus()
            elif action == 'select':
                self._stuck_strip.button.activate()
            return True
        return True

    def _configure_toolbars(self):
        """Create, set, and show a toolbar box with an activity button, game
        controls, difficulty selector, help button, and stop button. All
        callbacks are locally defined."""

        toolbar_box = ToolbarBox()
        toolbar = toolbar_box.toolbar

        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        toolbar.add(Gtk.SeparatorToolItem())

        def add_button(icon_name, tooltip, func):
            def callback(source):
                func()
            button = ToolButton(icon_name)
            toolbar.add(button)
            button.connect('clicked', callback)
            button.set_tooltip(tooltip)

        add_button('new-game'   , _("New")   , self._game.new_game)
        add_button('replay-game', _("Replay"), self._game.replay_game)

        toolbar.add(Gtk.SeparatorToolItem())

        add_button('edit-undo'  , _("Undo")  , self._game.undo)
        add_button('edit-redo'  , _("Redo")  , self._game.redo)

        toolbar.add(Gtk.SeparatorToolItem())

        self._levels_buttons = []
        def add_level_button(icon_name, tooltip, numeric_level):
            if self._levels_buttons:
                button = RadioToolButton(icon_name=icon_name,
                                         group=self._levels_buttons[0])
            else:
                button = RadioToolButton(icon_name=icon_name)
            self._levels_buttons.append(button)
            toolbar.add(button)

            def callback(source):
                if source.get_active():
                    self._game.set_level(numeric_level)
                    self._game.new_game()

            button.connect('clicked', callback)
            button.set_tooltip(tooltip)

        add_level_button('easy-level'  , _("Easy")  , 0)
        add_level_button('medium-level', _("Medium"), 1)
        add_level_button('hard-level'  , _("Hard")  , 2)

        self._add_expander(toolbar)

        def _help_clicked_cb():
            help_window = _HelpWindow()
            help_window.set_transient_for(self.get_toplevel())
            help_window.show_all()

        # NOTE: Naming the icon "help" instead of "help-icon" seems to use a
        # GTK stock icon instead of our custom help; the stock icon may be more
        # desireable in the future.  It doesn't seem to be themed for Sugar
        # right now, however.
        add_button('help-icon', _("Help"), _help_clicked_cb)

        stop_button = StopButton(self)
        stop_button.props.accelerator = '<Ctrl><Shift>Q'
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()

    def _add_expander(self, toolbar, expand=True):
        """Insert a toolbar item which will expand to fill the available
        space."""
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(expand)
        toolbar.insert(separator, -1)
        separator.show()


class _DialogWindow(Gtk.Window):
    # A base class for a modal dialog window.
    def __init__(self, icon_name, title):
        super(_DialogWindow, self).__init__()

        self.set_border_width(style.LINE_WIDTH)
        offset = style.GRID_CELL_SIZE
        width = Gdk.Screen.width() / 2
        height = Gdk.Screen.height() / 2
        self.set_size_request(width, height)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        toolbar = _DialogToolbar(icon_name, title)
        toolbar.connect('stop-clicked', self._stop_clicked_cb)
        vbox.pack_start(toolbar, expand=False, fill=False, padding=0)

        self.content_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_vbox.set_border_width(style.DEFAULT_SPACING)
        vbox.add(self.content_vbox)

        self.connect('realize', self._realize_cb)

    def _stop_clicked_cb(self, source):
        self.destroy()

    def _realize_cb(self, source):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.get_window().set_accept_focus(True)


class _HelpWindow(_DialogWindow):
    # A dialog window to display the game instructions.
    def __init__(self):
        super(_HelpWindow, self).__init__('help-icon', _("Help"))

        offset = style.GRID_CELL_SIZE
        width = Gdk.Screen.width() - offset * 2
        height = Gdk.Screen.height() - offset * 2
        self.set_size_request(width, height)

        self._help_widget = HelpWidget(self._icon_file)
        self.content_vbox.pack_start(self._help_widget, True, True, 0)

        self._help_nav_bar = _HelpNavBar()
        self.content_vbox.pack_end(self._help_nav_bar, expand=False,
                                   fill=False, padding=style.DEFAULT_SPACING)

        for (signal_name, callback) in [
                ('forward-clicked', self._forward_clicked_cb),
                ('reload-clicked', self._reload_clicked_cb),
                ('back-clicked', self._back_clicked_cb)]:
            self._help_nav_bar.connect(signal_name, callback)

        self._update_prev_next()

    def _forward_clicked_cb(self, source):
        self._help_widget.next_stage()
        self._update_prev_next()

    def _back_clicked_cb(self, source):
        self._help_widget.prev_stage()
        self._update_prev_next()

    def _reload_clicked_cb(self, source):
        self._help_widget.replay_stage()

    def _icon_file(self, icon_name):
        theme = Gtk.IconTheme.get_default()
        info = theme.lookup_icon(icon_name, 0, 0)
        return info.get_filename()

    def _update_prev_next(self):
        hw = self._help_widget
        self._help_nav_bar.set_can_prev_stage(hw.can_prev_stage())
        self._help_nav_bar.set_can_next_stage(hw.can_next_stage())


class _DialogToolbar(Gtk.Toolbar):
    # Displays a dialog window's toolbar, with title, icon, and close box.
    __gsignals__ = {
        'stop-clicked'       : (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    def __init__(self, icon_name, title):
        super(_DialogToolbar, self).__init__()

        icon = Icon()
        icon.set_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        self._add_widget(icon)

        self._add_separator()

        label = Gtk.Label(label=title)
        self._add_widget(label)

        self._add_separator(expand=True)

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Done'))
        stop.connect('clicked', self._stop_clicked_cb)
        self.add(stop)

    def _add_separator(self, expand=False):
        separator = Gtk.SeparatorToolItem()
        separator.set_expand(expand)
        separator.set_draw(False)
        self.add(separator)

    def _add_widget(self, widget):
        tool_item = Gtk.ToolItem()
        tool_item.add(widget)
        self.add(tool_item)

    def _stop_clicked_cb(self, button):
        self.emit('stop-clicked')


class _HelpNavBar(Gtk.HButtonBox):
    # A widget to display the navigation controls at the bottom of the help
    # dialog.
    __gsignals__ = {
        'forward-clicked' : (GObject.SignalFlags.RUN_LAST, None, ()),
        'back-clicked'    : (GObject.SignalFlags.RUN_LAST, None, ()),
        'reload-clicked'  : (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super(_HelpNavBar, self).__init__()

        self.set_layout(Gtk.ButtonBoxStyle.SPREAD)

        def add_button(icon_name, tooltip, signal_name):
            icon = Icon()
            icon.set_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
            button = Gtk.Button()
            button.set_image(icon)
            button.set_tooltip_text(tooltip)
            self.add(button)

            def callback(source):
                self.emit(signal_name)
            button.connect('clicked', callback)

            return button

        self._back_button = add_button('back', _("Previous"), 'back-clicked')
        add_button('reload', _("Again"), 'reload-clicked')
        self._forward_button = add_button('forward', _("Next"), 'forward-clicked')

    def set_can_prev_stage(self, can_prev_stage):
        self._back_button.set_sensitive(can_prev_stage)

    def set_can_next_stage(self, can_next_stage):
        self._forward_button.set_sensitive(can_next_stage)


class _StuckStrip(Gtk.Box):
    __gsignals__ = {
        'undo-clicked' : (GObject.SignalFlags.RUN_LAST, None, ()),
    }
    def __init__(self, *args, **kwargs):
        super(_StuckStrip, self).__init__(*args, **kwargs)

        self.orientation = Gtk.Orientation.HORIZONTAL

        spacer1 = Gtk.Label(label='')
        self.pack_start(spacer1, True, True, 0)

        spacer2 = Gtk.Label(label='')
        self.pack_end(spacer2, expand=True, fill=False, padding=0)

        self.set_spacing(10)

        self.set_border_width(10)

        label = Gtk.Label(label=_("Stuck?  You can still solve the puzzle."))
        self.pack_start(label, False, True, 0)

        icon = Icon()
        icon.set_from_icon_name('edit-undo', Gtk.IconSize.LARGE_TOOLBAR)
        self.button = Gtk.Button(stock=Gtk.STOCK_UNDO)
        self.button.set_image(icon)
        self.button.set_label(_("Undo some moves"))
        self.pack_end(self.button, expand=False, fill=False, padding=0)

        def callback(source):
            self.emit('undo-clicked')
        self.button.connect('clicked', callback)
