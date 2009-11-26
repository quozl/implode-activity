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

import gtk

KEY_MAP = {
    gtk.keysyms.KP_Up        : 'up',
    gtk.keysyms.KP_Down      : 'down',
    gtk.keysyms.KP_Left      : 'left',
    gtk.keysyms.KP_Right     : 'right',

    gtk.keysyms.w            : 'up',
    gtk.keysyms.s            : 'down',
    gtk.keysyms.a            : 'left',
    gtk.keysyms.d            : 'right',

    gtk.keysyms.KP_8         : 'up',
    gtk.keysyms.KP_2         : 'down',
    gtk.keysyms.KP_4         : 'left',
    gtk.keysyms.KP_6         : 'right',

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
    gtk.keysyms.KP_1         : 'select',
    gtk.keysyms.q            : 'select',

    gtk.keysyms.Home         : 'new',
    gtk.keysyms.KP_Home      : 'new',
    gtk.keysyms.Page_Down    : 'redo',
    gtk.keysyms.KP_Page_Down : 'redo',
    gtk.keysyms.Page_Up      : 'undo',
    gtk.keysyms.KP_Page_Up   : 'undo',
}
