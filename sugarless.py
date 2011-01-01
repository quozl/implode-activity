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

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import os

import implodegame
from helpwidget import HelpWidget
from keymap import KEY_MAP

_DEFAULT_SPACING = 15

class ImplodeWindow(gtk.Window):
    def __init__(self):
        super(ImplodeWindow, self).__init__(gtk.WINDOW_TOPLEVEL)
        self.set_geometry_hints(None, min_width=640, min_height=480)
        self.set_title("Implode")

        self.connect("delete_event", self._delete_event_cb)

        toolbar = gtk.Toolbar()
        self.game = implodegame.ImplodeGame()

        def add_button(id, func):
            button = gtk.ToolButton(id)
            toolbar.add(button)

            def callback(source):
                func()
            button.connect('clicked', callback)

            return button

        add_button(gtk.STOCK_NEW, self.game.new_game)
        add_button(gtk.STOCK_MEDIA_PREVIOUS, self.game.replay_game)
        add_button(gtk.STOCK_UNDO, self.game.undo)
        add_button(gtk.STOCK_REDO, self.game.redo)

        toolbar.add(gtk.SeparatorToolItem())

        radio_buttons = []
        def add_radio_button(label, func):
            button = gtk.RadioToolButton()
            button.set_label(label)
            toolbar.add(button)
            radio_buttons.append(button)

            def callback(source):
                if source.get_active():
                    func()
            button.connect('clicked', callback)

            return button

        add_radio_button('easy', self._easy_clicked)
        add_radio_button('medium', self._medium_clicked)
        add_radio_button('hard', self._hard_clicked)
        for button in radio_buttons[1:]:
            button.set_group(radio_buttons[0])

        separator = gtk.SeparatorToolItem()
        separator.set_expand(True)
        separator.set_draw(False)
        toolbar.add(separator)

        add_button(gtk.STOCK_HELP, self._help_clicked)

        self._stuck_strip = _StuckStrip()

        game_box = gtk.VBox()
        game_box.pack_start(self.game)
        game_box.pack_end(self._stuck_strip, expand=False)

        main_box = gtk.VBox()
        main_box.pack_start(toolbar, expand=False)
        main_box.pack_end(game_box)
        self.add(main_box)

        # Show everything except the stuck strip.
        main_box.show_all()
        self._stuck_strip.hide()

        self.game.connect('show-stuck', self._show_stuck_cb)
        self._stuck_strip.connect('undo-clicked', self._stuck_undo_cb)
        game_box.connect('key-press-event', self._key_press_event_cb)

        self.game.grab_focus()

        self.show()

    def _delete_event_cb(self, window, event):
        gtk.main_quit()
        return False

    def _easy_clicked(self):
        self.game.set_level(0)

    def _medium_clicked(self):
        self.game.set_level(1)

    def _hard_clicked(self):
        self.game.set_level(2)

    def _help_clicked(self):
        help_window = _HelpWindow()
        help_window.set_transient_for(self.get_toplevel())
        help_window.show_all()

    def _show_stuck_cb(self, state, data=None):
        if data:
            self._stuck_strip.show_all()
        else:
            if self._stuck_strip.focus_child:
                self.game.grab_focus()
            self._stuck_strip.hide()

    def _stuck_undo_cb(self, state, data=None):
        self.game.undo_to_solvable_state()

    def _key_press_event_cb(self, source, event):
        # Make the game navigable by keypad controls.
        action = KEY_MAP.get(event.keyval, None)
        if action is None:
            return False
        if not self._stuck_strip.flags() & gtk.VISIBLE:
            return True
        if self.game.focus_child:
            if action == 'down':
                self._stuck_strip.button.grab_focus()
            return True
        elif self._stuck_strip.focus_child:
            if action == 'up':
                self.game.grab_focus()
            elif action == 'select':
                self._stuck_strip.button.activate()
            return True
        return True

class _HelpWindow(gtk.Window):
    def __init__(self):
        super(_HelpWindow, self).__init__()

        self.set_size_request(640, 480)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.set_modal(True)

        vbox = gtk.VBox()
        self.add(vbox)

        self._help_widget = HelpWidget(self._icon_file)
        vbox.pack_start(self._help_widget)

        self._help_nav_bar = _HelpNavBar()
        vbox.pack_end(self._help_nav_bar,
                      expand=False)

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


class _HelpNavBar(gtk.HButtonBox):
    __gsignals__ = {
        'forward-clicked' : (gobject.SIGNAL_RUN_LAST, None, ()),
        'back-clicked'    : (gobject.SIGNAL_RUN_LAST, None, ()),
        'reload-clicked'  : (gobject.SIGNAL_RUN_LAST, None, ()),
    }

    def __init__(self):
        super(_HelpNavBar, self).__init__()

        self.set_layout(gtk.BUTTONBOX_SPREAD)

        def add_button(id, signal_name):
            button = gtk.Button(stock=id)
            self.add(button)

            def callback(source):
                self.emit(signal_name)
            button.connect('clicked', callback)

            return button

        self._back_button = add_button(gtk.STOCK_GO_BACK, 'back-clicked')
        add_button(gtk.STOCK_MEDIA_PLAY, 'reload-clicked')
        self._forward_button = add_button(gtk.STOCK_GO_FORWARD, 'forward-clicked')

    def set_can_prev_stage(self, can_prev_stage):
        self._back_button.set_sensitive(can_prev_stage)

    def set_can_next_stage(self, can_next_stage):
        self._forward_button.set_sensitive(can_next_stage)


class _StuckStrip(gtk.HBox):
    __gsignals__ = {
        'undo-clicked' : (gobject.SIGNAL_RUN_LAST, None, ()),
    }
    def __init__(self, *args, **kwargs):
        super(_StuckStrip, self).__init__(*args, **kwargs)

        spacer1 = gtk.Label('')
        self.pack_start(spacer1, expand=True)

        spacer2 = gtk.Label('')
        self.pack_end(spacer2, expand=True)

        self.set_spacing(10)

        self.set_border_width(10)

        label = gtk.Label("Stuck?  You can still solve the puzzle.")
        self.pack_start(label, expand=False)

        self.button = gtk.Button(stock=gtk.STOCK_UNDO)
        self.button.set_label("Undo some moves")
        self.pack_end(self.button, expand=False)

        def callback(source):
            self.emit('undo-clicked')
        self.button.connect('clicked', callback)


def main():
    w = ImplodeWindow()
    gtk.main()

if __name__ == "__main__":
    main()
