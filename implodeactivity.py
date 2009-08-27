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

from sugar.activity.activity import Activity, ActivityToolbox, get_bundle_path
from sugar.graphics import style
from sugar.graphics.icon import Icon
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.toolbutton import ToolButton

from implodegame import ImplodeGame
from helpwidget import HelpWidget

import os

try:
    import json
    json.dumps
except (ImportError, AttributeError):
    import simplejson as json
from StringIO import StringIO
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
        
        self._game = ImplodeGame()

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

        toolbox.connect('help-clicked', self._help_clicked_cb)

        self.set_canvas(self._game)
        self.show_all()
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

        print file_data
        _logger.debug(file_data)
        (file_type, version, game_data) = file_data
        if file_type == 'Implode save game' and version <= [1, 0]:
            self._game.set_game_state(game_data)

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

    def _help_clicked_cb(self, source):
        help_window = _HelpWindow()
        help_window.set_transient_for(self.get_toplevel())
        help_window.show_all()
        self.present()


class _Toolbox(ActivityToolbox):
    __gsignals__ = {
        'new-game-clicked'   : (gobject.SIGNAL_RUN_LAST, None, ()),
        'replay-game-clicked': (gobject.SIGNAL_RUN_LAST, None, ()),
        'undo-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
        'redo-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
        'easy-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
        'medium-clicked'     : (gobject.SIGNAL_RUN_LAST, None, ()),
        'hard-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
        'help-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
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
                button = RadioToolButton(named_icon=icon_name, group=levels[0])
            else:
                button = RadioToolButton(named_icon=icon_name)
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

        separator = gtk.SeparatorToolItem()
        separator.set_expand(True)
        separator.set_draw(False)
        toolbar.add(separator)

        # NOTE: Naming the icon "help" instead of "help-icon" seems to use a
        # GTK stock icon instead of our custom help; the stock icon may be more
        # desireable in the future.  It doesn't seem to be themed for Sugar
        # right now, however.
        add_button('help-icon', _("Help"), 'help-clicked')

        self.add_toolbar(_("Game"), toolbar)
        self.set_current_toolbar(1)


class _HelpWindow(gtk.Window):
    def __init__(self):
        super(_HelpWindow, self).__init__()

        self.set_border_width(style.LINE_WIDTH)
        offset = style.GRID_CELL_SIZE
        width = gtk.gdk.screen_width() - offset * 2
        height = gtk.gdk.screen_height() - offset * 2
        self.set_size_request(width, height)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS) 
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        vbox = gtk.VBox()
        self.add(vbox)

        toolbar = _HelpToolbar()
        toolbar.connect('stop-clicked', self._stop_clicked_cb)

        vbox.pack_start(toolbar, False)

        self._help_widget = HelpWidget(self._icon_file)
        vbox.pack_start(self._help_widget)

        self._help_nav_bar = _HelpNavBar()
        vbox.pack_end(self._help_nav_bar,
                      expand=False,
                      padding=style.DEFAULT_SPACING)

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
        activity_path = get_bundle_path()
        file_path = os.path.join(activity_path, 'icons', icon_name + '.svg')
        return file_path

    def _update_prev_next(self):
        hw = self._help_widget
        self._help_nav_bar.set_can_prev_stage(hw.can_prev_stage())
        self._help_nav_bar.set_can_next_stage(hw.can_next_stage())


class _HelpToolbar(gtk.Toolbar):
    __gsignals__ = {
        'stop-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
    }
    def __init__(self):
        super(_HelpToolbar, self).__init__()

        icon = Icon()
        icon.set_from_icon_name('help-icon', gtk.ICON_SIZE_LARGE_TOOLBAR)
        self._add_widget(icon)

        self._add_separator()

        label = gtk.Label(_("Help"))
        self._add_widget(label)

        self._add_separator(expand=True)

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Done'))
        stop.connect('clicked', self._stop_clicked_cb)
        self.add(stop)

    def _add_separator(self, expand=False):
        separator = gtk.SeparatorToolItem()
        separator.set_expand(expand)
        separator.set_draw(False)
        self.add(separator)

    def _add_widget(self, widget):
        tool_item = gtk.ToolItem()
        tool_item.add(widget)
        self.add(tool_item)

    def _stop_clicked_cb(self, button):
        self.emit('stop-clicked')


class _HelpNavBar(gtk.HButtonBox):
    __gsignals__ = {
        'forward-clicked' : (gobject.SIGNAL_RUN_LAST, None, ()),
        'back-clicked'    : (gobject.SIGNAL_RUN_LAST, None, ()),
        'reload-clicked'  : (gobject.SIGNAL_RUN_LAST, None, ()),
    }

    def __init__(self):
        super(_HelpNavBar, self).__init__()

        self.set_layout(gtk.BUTTONBOX_SPREAD)

        def add_button(icon_name, tooltip, signal_name):
            icon = Icon()
            icon.set_from_icon_name(icon_name, gtk.ICON_SIZE_LARGE_TOOLBAR)
            button = gtk.Button()
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


