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

import implodegame

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

        main_box = gtk.VBox(False, 0)
        main_box.pack_start(toolbar, False)
        main_box.pack_start(self.game, True, True, 0)
        self.add(main_box)

        self.show_all()
        self.game.grab_focus()

    def _delete_event_cb(self, window, event):
        gtk.main_quit()
        return False

    def _easy_clicked(self):
        print "Easy"

    def _medium_clicked(self):
        print "Medium"

    def _hard_clicked(self):
        print "Hard"


def main():
    w = ImplodeWindow()
    gtk.main()

if __name__ == "__main__":
    main()
