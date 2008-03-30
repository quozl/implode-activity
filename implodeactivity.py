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
_logger = logging.getLogger('implode-activity')

from gettext import gettext as _

from sugar.activity.activity import Activity, ActivityToolbox
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.radiotoolbutton import RadioToolButton

import implodegame

#import sys, os
import gtk
import gobject

_EASY = 0
_MEDIUM = 1
_HARD = 2

class ImplodeActivity(Activity):
    def hello(self, widget, data=None):
        logging.info("Hello World")

    def __init__(self, handle):
        super(ImplodeActivity, self).__init__(handle)

        _logger.debug('Starting implode activity...')
        
        self._game = implodegame.ImplodeGame()

        toolbox = _Toolbox(self)
        self.set_toolbox(toolbox)
        toolbox.show()

        for (signal, func) in (('new-game-clicked'   , self._game.new_game),
                               ('replay-game-clicked', self._game.replay_game),
                               ('undo-clicked'       , self._game.undo),
                               ('redo-clicked'       , self._game.redo)):
            def callback(source, func=func):
                func()
            toolbox.connect(signal, callback)

        for (signal, level) in (('easy-clicked'  , 0),
                                ('medium-clicked', 1),
                                ('hard-clicked'  , 2)):
            def callback(source, level=level):
                self._game.set_level(level)
            toolbox.connect(signal, callback)

        self.set_canvas(self._game)
        self.show_all()
        self._game.grab_focus()

class _Toolbox(ActivityToolbox):
    __gsignals__ = {
        'new-game-clicked'   : (gobject.SIGNAL_RUN_LAST, None, ()),
        'replay-game-clicked': (gobject.SIGNAL_RUN_LAST, None, ()),
        'undo-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
        'redo-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
        'easy-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
        'medium-clicked'     : (gobject.SIGNAL_RUN_LAST, None, ()),
        'hard-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
    }

    def __init__(self, activity):
        super(_Toolbox, self).__init__(activity)
   
        toolbar = gtk.Toolbar()

        def add_button(icon_name, tooltip, signal_name):
            button = ToolButton(icon_name)
            toolbar.add(button)
            
            def callback(source):
                self.emit(signal_name)
            button.connect('clicked', callback)
            button.set_tooltip(tooltip)

            return button

        add_button('new-game'   , _("New")   , 'new-game-clicked')
        add_button('replay-game', _("Replay"), 'replay-game-clicked')
        add_button('edit-undo'  , _("Undo")  , 'undo-clicked')
        add_button('edit-redo'  , _("Redo")  , 'redo-clicked')

        toolbar.add(gtk.SeparatorToolItem())

        levels = []
        def add_level_button(icon_name, tooltip, signal_name):
            if levels:
                button = RadioToolButton(icon_name, levels[0])
            else:
                button = RadioToolButton(icon_name)
            levels.append(button)
            toolbar.add(button)

            def callback(source):
                if source.get_active():
                    self.emit(signal_name)
            button.connect('clicked', callback)
            button.set_tooltip(tooltip)

        add_level_button('easy-level'  , _("Easy")  , 'easy-clicked')
        add_level_button('medium-level', _("Medium"), 'medium-clicked')
        add_level_button('hard-level'  , _("Hard")  , 'hard-clicked')

        self.add_toolbar(_("Game"), toolbar)
        self.set_current_toolbar(1)

