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

import random

class Board(object):
    """Object that defines a board containing pieces."""
    # Board is represented as a dict from x coordinates to lists representing
    # columns of pieces.  The beginning of the lists are the value of the piece
    # in the column at y=0, and subsequent values are for increasing values of
    # y.  Missing values are represented either with None in the column list or
    # a missing column in the dict.
    def __init__(self):
        self._data = {}

    def clone(self):
        """Return a copy of the board."""
        b = Board()
        for (col_index, col) in self._data.items():
            b._data[col_index] = col[:]
        return b

    def get_value(self, x, y):
        """Return the value at coordinate (x,y), or None if no value is
           present."""
        col = self._data.get(x, None)
        if col is None:
            return None
        if 0 <= y < len(col):
            return col[y]
        else:
            return None

    def set_value(self, x, y, value):
        """Set the value at coordinate (x,y) to the given value."""
        assert y >= 0

        col = self._data.get(x, None)
        if col is None:
            if value is not None:
                self._data[x] = [None] * y + [value]
        elif y < len(col):
            col[y] = value
            if value is None:
                self._trim_column(x)
        elif value is None:
            pass
        else:
            self._data[x] = col + [None] * (y - len(col)) + [value]

    def get_column_height(self, x):
        """Return the height of column x."""
        col = self._data.get(x, None)
        if col is None:
            return 0
        else:
            return len(col)

    @property
    def width(self):
        return (self.max_x - self.min_x)

    @property
    def height(self):
        return (self.max_y - self.min_y)

    @property
    def min_x(self):
        if len(self._data) == 0:
            return 0
        else:
            return min(0, min(self._data.keys()))

    @property
    def max_x(self):
        if len(self._data) == 0:
            return 0
        else:
            return max(0, max(self._data.keys())) + 1

    @property
    def min_y(self):
        return 0

    @property
    def max_y(self):
        if len(self._data) == 0:
            return 0
        else:
            return max(0, max(len(col) for col in self._data.values()))

    def is_empty(self):
        return (len(self._data) == 0)

    def get_value_map(self):
        """Returns a map from coordinate tuples to values for all cells on the
           board."""
        value_map = {}
        for (i, col) in self._data.items():
            for (j, value) in enumerate(col):
                if value is not None:
                    value_map[(i, j)] = value
        return value_map

    def _trim_column(self, x):
        # Removes any None values at the top of the given column, removing the
        # column array entirely if it is empty.
        col = self._data[x]
        if col[-1] is not None:
            return
        for i in range(len(col) - 1, -1, -1):
            if col[i] is not None:
                self._data[x] = col[:i+1]
                return
        del self._data[x]

    def get_all_contiguous(self):
        """Returns a collection of all contiguous shapes with size >= 3,
           where each contiguous shape is represented as a set of coordinate
           tuples."""
        examined = set()
        all_contiguous = []
        for (i, col) in self._data.items():
            for (j, value) in enumerate(col):
                coord = (i, j)
                if coord not in examined:
                    examined.add(coord)
                    contiguous = self.get_contiguous(*coord)
                    examined.update(contiguous)
                    if len(contiguous) >= 3:
                        all_contiguous.append(contiguous)
        return all_contiguous

    def get_contiguous(self, x, y):
        """Given a board coordinate, returns a set of all the coordinate
           tuples that are contiguous and have the same value."""

        value = self.get_value(x, y)
        if value is None:
            return set()

        # Add the start location to the candidate and examined sets.
        candidates = set()
        candidates.add((x, y))
        examined = set()
        examined.add((x, y))

        # Build the contiguous set.
        contiguous = set()
        while len(candidates) > 0:
            coord = candidates.pop()
            if self.get_value(coord[0], coord[1]) == value:
                # If the candidate has the value we're looking for, add it
                # to the contiguous set and add its unexamined neighbors to
                # the candidate and examined sets.
                contiguous.add(coord)
                for (x_offset, y_offset) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    coord2 = (coord[0] + x_offset, coord[1] + y_offset)
                    if coord2 not in examined:
                        examined.add(coord2)
                        candidates.add(coord2)
        return contiguous

    def remove_empty_columns(self):
        """Removes columns that are empty."""
        new_data = {}
        for i in sorted(self._data.keys()):
            new_data[len(new_data)] = self._data[i]
        self._data = new_data

    def get_slide_map(self):
        """Returns a map showing where sliding pieces will go when empty
           columns are removed, as a dictionary mapping old x coordinates
           to new x coordinates.  Does not include entries where the old
           x coordinates are the same as the new ones."""
        slide_map = {}
        for (i, x) in enumerate(sorted(self._data.keys())):
            if i != x:
                slide_map[x] = i
        return slide_map

    def clear_pieces(self, pieces):
        """Given a set of coordinate tuples, removes their contents from the
           board."""
        for (x, y) in pieces:
            self.set_value(x, y, None)

    def insert_columns(self, col_index, num_columns):
        """Inserts empty columns at the given index, pushing higher-numbered
           columns higher."""
        assert num_columns >= 0
        new_data = {}
        for (i, col) in self._data.items():
            if i < col_index:
                new_data[i] = col
            else:
                new_data[i + num_columns] = col
        self._data = new_data

    def delete_columns(self, col_index, num_columns):
        """Removes columns from the given location of the board, lowering the
           higher-numbered columns to fill the space."""
        assert 0 <= num_columns
        new_data = {}
        for (i, col) in self._data.items():
            if i < col_index:
                new_data[i] = col
            elif i >= col_index + num_columns:
                new_data[i - num_columns] = col
        self._data = new_data

    def get_empty_columns(self):
        """Returns a list of empty (all zero) columns."""
        empty_cols = []
        for i in range(min(0, self.min_x), self.max_x):
            if i not in self._data.items():
                empty_cols.append(i)
        return empty_cols

    def drop_pieces(self):
        for (i, col) in self._data.items():
            self._data[i] = [x for x in col if x is not None]

    def get_drop_map(self):
        """Returns a map showing where dropped pieces will go (compacting
           out None values vertically), as a dictionary mapping old
           coordinate tuples to new coordinate tuples."""
        drop_map = {}
        for (i, col) in self._data.items():
            offset = 0
            for (j, value) in enumerate(col):
                if value is not None:
                    drop_map[(i, j)] = (i, offset)
                    offset += 1
        return drop_map

    def __eq__(self, other):
        return (self._data == other._data)

    def __neq__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        width = self.width
        height = self.height
        lines = []
        for i in reversed(range(height)):
            line = []
            for j in range(width):
                value = self.get_value(j, i)
                if value is None:
                    line.append('.')
                elif value == -1:
                    line.append('*')
                else:
                    line.append(str(value))
            lines.append(''.join(line))
        return '\n'.join(lines)

def make_test_board(width, height):
    b = Board()
    r = random.Random()
    r.seed(0)
    unchosen = []
    for x in range(width):
        for y in range(height):
            unchosen.append((x, y))
    for i in range(width * height * 4 / 6):
        coord = r.choice(unchosen)
        unchosen.remove(coord)
        b.set_value(coord[0], coord[1], r.randint(0, 2))
    for i in range(10 + 1):
        b.set_value(i, 0, i)
    return b

def dump_board(b):
    print repr(b)

def main():
    b = make_test_board(30, 20)
    dump_board(b)
    print b.get_all_contiguous()

if __name__ == '__main__':
    main()
