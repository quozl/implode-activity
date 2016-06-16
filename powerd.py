# Copyright (C) 2011 One Laptop per Child
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty ofwa
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os


def fake():
    """ Generate fake activity that will be treated as user activity.

    Gracefully degrades if the system does not have powerd installed.

    From olpc-powerd: the modification time of the file .fake_activity
    will be checked before any sleep occurs, and will be compared to
    the time of the last 'real' user activity.  If it is newer, the
    dim/blank/sleep will be skipped.  So a program wishing to indicate
    that it is 'active' can simply touch this file periodically to
    keep it up-to-date.  """
    name = '/var/run/powerd-inhibit-suspend/.fake_activity'
    try:
        os.utime(name, None)
    except OSError:
        pass
