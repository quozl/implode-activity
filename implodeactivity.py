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

from sugar.activity.activity import Activity, get_bundle_path
from sugar.graphics import style
from sugar.graphics.icon import Icon
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.toolbutton import ToolButton

try:
    # 0.86+ toolbar widgets
    from sugar.activity.widgets import ActivityToolbarButton, StopButton
    from sugar.graphics.toolbarbox import ToolbarBox, ToolbarButton
    _USE_OLD_TOOLBARS = False
except ImportError:
    # Pre-0.86 toolbar widgets
    from sugar.activity.activity import ActivityToolbox
    _USE_OLD_TOOLBARS = True

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

from keymap import KEY_MAP

class ImplodeActivity(Activity):
    def hello(self, widget, data=None):
        logging.info("Hello World")

    def __init__(self, handle):
        super(ImplodeActivity, self).__init__(handle)

        _logger.debug('Starting implode activity...')

        self._game = ImplodeGame()
        self._game.connect('stuck', self._stuck_cb)

        self._configure_toolbars()

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

    def _stuck_cb(self, state):
        stuck_window = _StuckWindow(self._game)
        stuck_window.set_transient_for(self.get_toplevel())
        stuck_window.show_all()

    def _configure_toolbars(self):
        """Create, set, and show a toolbar box with an activity button, game
        controls, difficulty selector, help button, and stop button. All
        callbacks are locally defined."""

        if _USE_OLD_TOOLBARS:
            toolbox = ActivityToolbox(self)
            toolbar = gtk.Toolbar()
        else:
            toolbar_box = ToolbarBox()
            toolbar = toolbar_box.toolbar

            activity_button = ActivityToolbarButton(self)
            toolbar_box.toolbar.insert(activity_button, 0)
            activity_button.show()

            self._add_expander(toolbar_box.toolbar)

            toolbar.add(gtk.SeparatorToolItem())

        def add_button(icon_name, tooltip, func):
            def callback(source):
                func()
            button = ToolButton(icon_name)
            toolbar.add(button)
            button.connect('clicked', callback)
            button.set_tooltip(tooltip)

        add_button('new-game'   , _("New")   , self._game.new_game)
        add_button('replay-game', _("Replay"), self._game.replay_game)
        add_button('edit-undo'  , _("Undo")  , self._game.undo)
        add_button('edit-redo'  , _("Redo")  , self._game.redo)

        toolbar.add(gtk.SeparatorToolItem())

        self._levels_buttons = []
        def add_level_button(icon_name, tooltip, numeric_level):
            if self._levels_buttons:
                button = RadioToolButton(named_icon=icon_name,
                                         group=self._levels_buttons[0])
            else:
                button = RadioToolButton(named_icon=icon_name)
            self._levels_buttons.append(button)
            toolbar.add(button)

            def callback(source):
                if source.get_active():
                    self._game.set_level(numeric_level)

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

        if _USE_OLD_TOOLBARS:
            toolbox.add_toolbar(_("Game"), toolbar)
            toolbox.set_current_toolbar(1)

            self.set_toolbox(toolbox)
            toolbox.show()
        else:
            stop_button = StopButton(self)
            stop_button.props.accelerator = '<Ctrl><Shift>Q'
            toolbar_box.toolbar.insert(stop_button, -1)
            stop_button.show()

            self.set_toolbar_box(toolbar_box)
            toolbar_box.show()

    def _add_expander(self, toolbar):
        """Insert a toolbar item which will expand to fill the available
        space."""
        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar.insert(separator, -1)
        separator.show()


class _DialogWindow(gtk.Window):
    # A base class for a modal dialog window.
    def __init__(self, icon_name, title):
        super(_DialogWindow, self).__init__()

        self.set_border_width(style.LINE_WIDTH)
        offset = style.GRID_CELL_SIZE
        width = gtk.gdk.screen_width() / 2
        height = gtk.gdk.screen_height() / 2
        self.set_size_request(width, height)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        vbox = gtk.VBox()
        self.add(vbox)

        toolbar = _DialogToolbar(icon_name, title)
        toolbar.connect('stop-clicked', self._stop_clicked_cb)
        vbox.pack_start(toolbar, False)

        self.content_vbox = gtk.VBox()
        self.content_vbox.set_border_width(style.DEFAULT_SPACING)
        vbox.add(self.content_vbox)

        self.connect('realize', self._realize_cb)

    def _stop_clicked_cb(self, source):
        self.destroy()

    def _realize_cb(self, source):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.window.set_accept_focus(True)


class _StuckWindow(_DialogWindow):
    # A dialog window to prompt the user when a game can't be finished.
    def __init__(self, game):
        super(_StuckWindow, self).__init__('help-icon', _("Stuck"))

        width = gtk.gdk.screen_width() / 2
        height = gtk.gdk.screen_height() / 2
        self.set_size_request(width, height)

        label = gtk.Label(_("Stuck?  You can still solve the puzzle."))
        label.set_line_wrap(True)
        self.content_vbox.pack_start(label,
                                     expand=False,
                                     padding=style.DEFAULT_SPACING)

        def add_button(icon_name, label, func):
            icon = Icon()
            icon.set_from_icon_name(icon_name, gtk.ICON_SIZE_LARGE_TOOLBAR)
            button = gtk.Button()
            button.set_image(icon)
            button.set_label(label)
            self.content_vbox.pack_start(button,
                                         expand=True,
                                         padding=style.DEFAULT_SPACING)

            def callback(source):
                self.destroy()
                func()
            button.connect('clicked', callback)

            return button

        undo = add_button('edit-undo', _("Undo"), game.undo_to_solvable_state)
        new = add_button('new-game', _("New game"), game.new_game)

        _add_button_nav_override(new, undo)
        _add_button_nav_override(undo, new)
        undo.grab_focus()

class _HelpWindow(_DialogWindow):
    # A dialog window to display the game instructions.
    def __init__(self):
        super(_HelpWindow, self).__init__('help-icon', _("Help"))

        offset = style.GRID_CELL_SIZE
        width = gtk.gdk.screen_width() - offset * 2
        height = gtk.gdk.screen_height() - offset * 2
        self.set_size_request(width, height)

        self._help_widget = HelpWidget(self._icon_file)
        self.content_vbox.pack_start(self._help_widget)

        self._help_nav_bar = _HelpNavBar()
        self.content_vbox.pack_end(self._help_nav_bar,
                                   expand=False,
                                   padding=style.DEFAULT_SPACING)

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
        activity_path = get_bundle_path()
        file_path = os.path.join(activity_path, 'icons', icon_name + '.svg')
        return file_path

    def _update_prev_next(self):
        hw = self._help_widget
        self._help_nav_bar.set_can_prev_stage(hw.can_prev_stage())
        self._help_nav_bar.set_can_next_stage(hw.can_next_stage())


class _DialogToolbar(gtk.Toolbar):
    # Displays a dialog window's toolbar, with title, icon, and close box.
    __gsignals__ = {
        'stop-clicked'       : (gobject.SIGNAL_RUN_LAST, None, ()),
    }
    def __init__(self, icon_name, title):
        super(_DialogToolbar, self).__init__()

        icon = Icon()
        icon.set_from_icon_name(icon_name, gtk.ICON_SIZE_LARGE_TOOLBAR)
        self._add_widget(icon)

        self._add_separator()

        label = gtk.Label(title)
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
    # A widget to display the navigation controls at the bottom of the help
    # dialog.
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

# It is important that the "stuck" window buttons be navigable with the keypad,
# so that the bulk of the game can be played in tablet mode on the XO.  To
# facilitate this, we add a key press override for one button to:
#   - Make it switch focus to the other button on a directional keypress
#   - Make it activate the button on a select keypress.
#
# There is probably a better way to do this... I have tried a number of
# different key capture/focus approaches, and the gtk in my Sugar emulator so
# far has not cooperated... which is odd, since the gtk on my desktop does the
# right thing by default.
def _add_button_nav_override(button, other_button):
    def key_press_event_cb(widget, event, data=None):
        action = KEY_MAP.get(event.keyval, None)
        if action in ('left', 'right', 'up', 'down'):
            other_button.grab_focus()
            return True
        if action == 'select':
            button.activate()
            return True
        return False
    button.connect('key-press-event', key_press_event_cb)

