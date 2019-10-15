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

# A stub file for running the application on a sugarless GTK, when the Activity
# framework is not available.

import os
import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Rsvg', '2.0')

from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gtk

import implodegame
from helpwidget import HelpWidget
from keymap import KEY_MAP

_DEFAULT_SPACING = 15


class ImplodeWindow(Gtk.Window):
    def __init__(self):
        super(ImplodeWindow, self).__init__(Gtk.WindowType.TOPLEVEL)

        geometry = Gdk.Geometry()
        (geometry.min_width, geometry.min_height) = (640, 480)
        hints = Gdk.WindowHints(Gdk.WindowHints.MIN_SIZE)
        self.set_geometry_hints(None, geometry, hints)

        self.set_title("Implode")

        self.connect("delete_event", self._delete_event_cb)

        toolbar = Gtk.Toolbar()
        toolbar.props.icon_size = 32

        self._game = implodegame.ImplodeGame()

        icon_theme = Gtk.IconTheme()
        icon_theme.set_search_path(['icons'])

        def set_icon(button, icon):
            image = Gtk.Image()
            pixbuf = icon_theme.load_icon(icon, toolbar.props.icon_size, 0)
            image.set_from_pixbuf(pixbuf)
            button.set_icon_widget(image)

        def add_button(icon, func):
            button = Gtk.ToolButton()
            set_icon(button, icon)
            toolbar.add(button)

            def callback(source):
                func()
            button.connect('clicked', callback)

            return button

        add_button('new-game', self._game.new_game)
        add_button('replay-game', self._game.replay_game)
        add_button('edit-undo', self._game.undo)
        add_button('edit-redo', self._game.redo)

        toolbar.add(Gtk.SeparatorToolItem())

        radio_buttons = []

        def add_radio_button(icon, func):
            if radio_buttons:
                button = Gtk.RadioToolButton(group=radio_buttons[0])
            else:
                button = Gtk.RadioToolButton()
            set_icon(button, icon)
            radio_buttons.append(button)
            toolbar.add(button)

            def callback(source):
                if source.get_active():
                    func()
            button.connect('clicked', callback)

            return button

        add_radio_button('easy-level', self._easy_clicked)
        add_radio_button('medium-level', self._medium_clicked)
        add_radio_button('hard-level', self._hard_clicked)

        separator = Gtk.SeparatorToolItem()
        separator.set_expand(True)
        separator.set_draw(False)
        toolbar.add(separator)

        add_button('toolbar-help', self._help_clicked)

        self._stuck_strip = _StuckStrip()

        game_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        game_box.pack_start(self._game, True, True, 0)
        game_box.pack_end(self._stuck_strip, False, False, 0)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.pack_start(toolbar, False, True, 0)
        main_box.pack_end(game_box, True, True, 0)
        self.add(main_box)

        # Show everything except the stuck strip.
        main_box.show_all()
        self._stuck_strip.hide()

        self._game.connect('show-stuck', self._show_stuck_cb)
        self._stuck_strip.connect('undo-clicked', self._stuck_undo_cb)
        game_box.connect('key-press-event', self._key_press_event_cb)

        self._game.grab_focus()

        self.show()

    def _delete_event_cb(self, window, event):
        Gtk.main_quit()
        return False

    def _easy_clicked(self):
        self._game.set_level(0)

    def _medium_clicked(self):
        self._game.set_level(1)

    def _hard_clicked(self):
        self._game.set_level(2)

    def _help_clicked(self):
        help_window = _HelpWindow()
        help_window.set_transient_for(self.get_toplevel())
        help_window.show_all()

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


class _HelpWindow(Gtk.Window):
    def __init__(self):
        super(_HelpWindow, self).__init__()

        self.set_size_request(640, 480)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_modal(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        self._help_widget = HelpWidget(self._icon_file)
        vbox.pack_start(self._help_widget, True, True, 0)

        self._help_nav_bar = _HelpNavBar()
        vbox.pack_end(self._help_nav_bar, False, False, _DEFAULT_SPACING)

        for (signal_name, callback) in [
                ('forward-clicked', self._forward_clicked_cb),
                ('reload-clicked', self._reload_clicked_cb),
                ('back-clicked', self._back_clicked_cb)]:
            self._help_nav_bar.connect(signal_name, callback)

        self._update_prev_next()

    def _stop_clicked_cb(self, source):
        self.destroy()

    def _forward_clicked_cb(self, source):
        self._help_widget.next_stage()
        self._update_prev_next()

    def _back_clicked_cb(self, source):
        self._help_widget.prev_stage()
        self._update_prev_next()

    def _reload_clicked_cb(self, source):
        self._help_widget.replay_stage()

    def _icon_file(self, icon_name):
        return os.path.join('icons', icon_name + '.svg')

    def _update_prev_next(self):
        hw = self._help_widget
        self._help_nav_bar.set_can_prev_stage(hw.can_prev_stage())
        self._help_nav_bar.set_can_next_stage(hw.can_next_stage())


class _HelpNavBar(Gtk.HButtonBox):
    # A widget to display the navigation controls at the bottom of the help
    # dialog.
    __gsignals__ = {
        'forward-clicked': (GObject.SignalFlags.RUN_LAST, None, ()),
        'back-clicked': (GObject.SignalFlags.RUN_LAST, None, ()),
        'reload-clicked': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super(_HelpNavBar, self).__init__()

        self.set_layout(Gtk.ButtonBoxStyle.SPREAD)

        def add_button(id, signal_name):
            button = Gtk.Button(stock=id)
            self.add(button)

            def callback(source):
                self.emit(signal_name)
            button.connect('clicked', callback)

            return button

        self._back_button = add_button(Gtk.STOCK_GO_BACK, 'back-clicked')
        add_button(Gtk.STOCK_MEDIA_PLAY, 'reload-clicked')
        self._forward_button = add_button(Gtk.STOCK_GO_FORWARD,
                                          'forward-clicked')

    def set_can_prev_stage(self, can_prev_stage):
        self._back_button.set_sensitive(can_prev_stage)

    def set_can_next_stage(self, can_next_stage):
        self._forward_button.set_sensitive(can_next_stage)


class _StuckStrip(Gtk.Box):
    __gsignals__ = {
        'undo-clicked': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, *args, **kwargs):
        super(_StuckStrip, self).__init__(*args, **kwargs)

        self.orientation = Gtk.Orientation.HORIZONTAL

        spacer1 = Gtk.Label('')
        self.pack_start(spacer1, True, True, 0)

        spacer2 = Gtk.Label('')
        self.pack_end(spacer2, True, False, 0)

        self.set_spacing(10)

        self.set_border_width(10)

        label = Gtk.Label("Stuck?  You can still solve the puzzle.")
        self.pack_start(label, False, True, 0)

        self.button = Gtk.Button(stock=Gtk.STOCK_UNDO)
        self.button.set_label("Undo some moves")
        self.pack_end(self.button, False, False, 0)

        def callback(source):
            self.emit('undo-clicked')
        self.button.connect('clicked', callback)


def main():
    w = ImplodeWindow()
    Gtk.main()
    del w

if __name__ == "__main__":
    main()
