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

from gi.repository import Gdk

KEY_MAP = {
    Gdk.KEY_KP_Up        : 'up',
    Gdk.KEY_KP_Down      : 'down',
    Gdk.KEY_KP_Left      : 'left',
    Gdk.KEY_KP_Right     : 'right',

    Gdk.KEY_w            : 'up',
    Gdk.KEY_s            : 'down',
    Gdk.KEY_a            : 'left',
    Gdk.KEY_d            : 'right',

    Gdk.KEY_KP_8         : 'up',
    Gdk.KEY_KP_2         : 'down',
    Gdk.KEY_KP_4         : 'left',
    Gdk.KEY_KP_6         : 'right',

    Gdk.KEY_Up           : 'up',
    Gdk.KEY_Down         : 'down',
    Gdk.KEY_Left         : 'left',
    Gdk.KEY_Right        : 'right',

    Gdk.KEY_uparrow      : 'up',
    Gdk.KEY_downarrow    : 'down',
    Gdk.KEY_leftarrow    : 'left',
    Gdk.KEY_rightarrow   : 'right',

    Gdk.KEY_Return       : 'select',
    Gdk.KEY_KP_Space     : 'select',
    Gdk.KEY_KP_Enter     : 'select',
    Gdk.KEY_space        : 'select',
    Gdk.KEY_End          : 'select',
    Gdk.KEY_KP_End       : 'select',
    Gdk.KEY_KP_1         : 'select',
    Gdk.KEY_q            : 'select',

    Gdk.KEY_Home         : 'new',
    Gdk.KEY_KP_Home      : 'new',
    Gdk.KEY_Page_Down    : 'redo',
    Gdk.KEY_KP_Page_Down : 'redo',
    Gdk.KEY_Page_Up      : 'undo',
    Gdk.KEY_KP_Page_Up   : 'undo',
}
