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

import math
import random

import board

def generate_board(seed=0,
                   fragmentation=1,
                   fill=0.5,
                   max_colors=5,
                   max_size=(30,20)):
    """Generates a new board of the given properties using the given random
       seed as a starting point."""
    r = random.Random(seed)
    piece_sizes = _get_piece_sizes(r, fragmentation, fill, max_size)
    b = board.Board()
    for piece_size in piece_sizes:
        b = _try_add_piece(b, r, piece_size, max_colors, max_size)
    return b

def _try_add_piece(b, r, piece_size, max_colors, max_size):
    # Tries to add a piece of the given size to the board.  Returns the
    # modified board on success or the original board on failure.
    b2 = b.clone()
    change = _get_starting_change(b2, r, max_colors, max_size)
    if change is None:
        # If there are no valid starting points, return the original board.
        return b
    _make_change(b2, change)
    total_added_cells = 1
    while total_added_cells < piece_size:
        added_cells = _try_add_cells(b2, r, max_colors, max_size)
        if added_cells > 0:
            total_added_cells += added_cells
        else:
            # If we have added a valid piece, return the modified board;
            # otherwise return the original board.
            if total_added_cells >= 3:
                break
            else:
                #print "Aborted piece add."
                return b
    _color_piece_random(b2, r, max_colors)
    return b2

def _get_starting_change(b, r, max_colors, max_size):
    # Gets a valid initial change that adds a one-cell colorable piece to the
    # board, returning None if no such starting change exists.
    changes = _enumerate_one_cell_changes(b, max_size)
    while len(changes) > 0:
        change = r.choice(changes)
        changes.remove(change)
        if _change_is_colorable(b, change, max_colors):
            return change
    return None

def _enumerate_one_cell_changes(b, max_size):
    # Returns a list of all possible one-cell changes.
    (max_width, max_height) = max_size
    changes = []
    width = b.width
    if width < max_width and max_height >= 1:
        for i in range(width + 1):
            changes.append(_InsertColumnChange(i, 1))
    for i in range(width):
        col_height = b.get_column_height(i)
        if col_height < max_height:
            for j in range(col_height + 1):
                changes.append(_InsertCellChange(i, j))
    return changes

def _try_add_cells(b, r, max_colors, max_size):
    # Tries to add a cell or cells to the new piece on the board in a way that
    # ensures the resulting board is within the given board size and is
    # colorable with the given colors.  Returns the number of cells added
    # (zero, if no cell could be added).
    (cell_h_changes, cell_v_changes) = _get_cell_changes(b, max_size)
    col_changes = _get_col_changes(b, max_size)
    while (len(cell_h_changes) > 0
           or len(cell_v_changes) > 0
           or len(col_changes) > 0):
        change = _remove_change(r, cell_h_changes, cell_v_changes, col_changes)
        if _change_is_colorable(b, change, max_colors):
            _make_change(b, change)
            #print
            #print change
            #print b
            if isinstance(change, _InsertCellChange):
                return 1
            else:
                return change.height
    return 0

def _get_cell_changes(b, max_size):
    # Returns a list of all possible standard cell insertions.
    (max_width, max_height) = max_size
    h_changes = []
    v_changes = []
    width = b.width
    for i in range(width):
        col_height = b.get_column_height(i)
        if col_height < max_height:
            for j in range(col_height + 1):
                if b.get_value(i, j) != -1:
                    if (b.get_value(i + 1, j) == -1 or
                        b.get_value(i - 1, j) == -1):
                        h_changes.append(_InsertCellChange(i, j))
                    elif (b.get_value(i, j - 1) == -1 or
                          b.get_value(i, j + 1) == -1):
                        v_changes.append(_InsertCellChange(i, j))
    return h_changes, v_changes

def _get_col_changes(b, max_size):
    # Returns a list of all possible column insertions.
    (max_width, max_height) = max_size
    width = b.width
    if width == max_width or max_height < 1:
        return []
    highest_new_pieces = []
    for i in range(width):
        col_height = b.get_column_height(i)
        highest_new_piece = 0
        for j in range(col_height):
            value = b.get_value(i, j)
            if value == -1:
                highest_new_piece = j + 1
        highest_new_pieces.append(highest_new_piece)
    changes = []
    for (i, (height1, height2)) in enumerate(zip(highest_new_pieces + [0],
                                                 [0] + highest_new_pieces)):
        height = max(height1, height2)
        if height > 0:
            changes.append(_InsertColumnChange(i, height))
    return changes

def _remove_change(r, cell_h_changes, cell_v_changes, col_changes):
    # Removes a change from cell changes or col changes (less likely) and
    # returns it.
    h_weight = len(cell_h_changes) * 10
    v_weight = len(cell_v_changes) * 5 
    col_weight = len(col_changes) * 1
    value = r.randint(0, h_weight + v_weight + col_weight - 1)
    if value < h_weight:
        return _pick(r, cell_h_changes)
    elif value < h_weight + v_weight:
        return _pick(r, cell_v_changes)
    else:
        return _pick(r, col_changes)

def _pick(r, items):
    index = r.randint(0, len(items) - 1)
    return items.pop(index)

def _change_is_colorable(b, change, max_colors):
    # Returns True if the board is still colorable after the given change is
    # made, False otherwise.
    b2 = b.clone()
    _make_change(b2, change)
    colors = _get_new_piece_colors(b2, max_colors)
    return len(colors) > 0

def _make_change(b, change):
    # Makes the given change to the board (side-affects board parameter).
    if isinstance(change, _InsertColumnChange):
        b.insert_columns(change.col, 1)
        for i in range(change.height):
            b.set_value(change.col, i, -1)
    elif isinstance(change, _InsertCellChange):
        new_indexes = []
        data = []
        col_height = b.get_column_height(change.col)
        assert change.height <= col_height
        for i in range(col_height):
            value = b.get_value(change.col, i)
            if i == change.height:
                data.append(-1)
            if value == -1:
                new_indexes.append(i)
            else:
                data.append(value)
        if change.height == col_height:
            data.append(-1)
        for index in new_indexes:
            data.insert(index, -1)
        for (i, value) in enumerate(data):
            b.set_value(change.col, i, value)
    else:
        assert False

def _color_piece_random(b, r, max_colors):
    # Colors in the new piece on the board with a random color using the given
    # random number generator and number of colors.
    colors = _get_new_piece_colors(b, max_colors)
    color = r.choice(list(colors))
    _color_piece(b, color)

def _color_piece(b, color):
    # Colors in the new piece on the board with the given color.
    coords = _get_new_piece_coords(b)
    for (i, j) in coords:
        b.set_value(i, j, color)

def _get_new_piece_colors(b, max_colors):
    # Returns the set of possible colors for the new piece.
    colors = set(range(1, max_colors + 1))
    coords = _get_new_piece_coords(b)
    for (i, j) in coords:
        for (x_ofs, y_ofs) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            colors.discard(b.get_value(i + x_ofs, j + y_ofs))
    return colors

def _get_new_piece_coords(b):
    # Returns a list of new piece coordinates.
    coords = []
    for i in range(b.width):
        col_height = b.get_column_height(i)
        for j in range(col_height):
            if b.get_value(i, j) == -1:
                coords.append((i, j))
    return coords

def _get_piece_sizes(r, fragmentation, fill, max_size):
    # Returns a list containing the new piece sizes for the board using the
    # given random number generator, fragmentation, fill, and board size.
    max_area = max_size[0] * max_size[1] * fill
    total_area = 0
    piece_sizes = []
    while total_area < max_area:
        piece_size = _get_piece_size(r, fragmentation, max_area)
        total_area += piece_size
        piece_sizes.append(piece_size)
    #print piece_sizes
    return piece_sizes

def _get_piece_size(r, fragmentation, max_area):
    # Returns a random piece size using the given random number generator,
    # fragmentation, and board size.
    upper_bound = math.ceil(math.sqrt(max_area))
    value = r.random()
    exp = fragmentation
    piece_size = int(max(3, math.pow(value, exp) * upper_bound))
    return piece_size

class _InsertColumnChange(object):
    # Represents the action of inserting a column into the board at column
    # "col" containing "height" cells.
    def __init__(self, col, height):
        self.col = col
        self.height = height

    def __eq__(self, other):
        return (isinstance(other, _InsertColumnChange)
                and self.col == other.col
                and self.height == other.height)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "_InsertColumnChange(%d, %d)" % (self.col, self.height)

class _InsertCellChange(object):
    # Represents the action of inserting a cell into the board in column
    # "col" at height "height".
    def __init__(self, col, height):
        self.col = col
        self.height = height

    def __eq__(self, other):
        return (isinstance(other, _InsertCellChange)
                and self.col == other.col
                and self.height == other.height)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "_InsertCellChange(%d, %d)" % (self.col, self.height)

def main():
    b = generate_board(seed=1,
                       fragmentation=1,
                       max_colors=5,
                       max_size=(20,10))
    print repr(b)

if __name__ == '__main__':
    #import cProfile
    #cProfile.run('main()', 'genprof')
    #import pstats
    #p = pstats.Stats('genprof')
    #p.strip_dirs().sort_stats(-1).print_stats()
    main()
