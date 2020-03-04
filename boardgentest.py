#!/usr/bin/python2
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

import unittest

import board
import boardgen


class TestEnumerateOneCellChanges(unittest.TestCase):

    def test1(self):
        b = board.Board()
        expChanges = [boardgen._InsertColumnChange(0, 1)]
        changes = boardgen._enumerate_one_cell_changes(b, (1, 1))
        self._assertChanges(changes, expChanges)

    def test2(self):
        b = board.Board()
        expChanges = []
        changes = boardgen._enumerate_one_cell_changes(b, (0, 1))
        self._assertChanges(changes, expChanges)

    def test3(self):
        b = board.Board()
        expChanges = []
        changes = boardgen._enumerate_one_cell_changes(b, (1, 0))
        self._assertChanges(changes, expChanges)

    def test4(self):
        b = _make_board(""".1.
                           211""")
        cell = boardgen._InsertCellChange
        col = boardgen._InsertColumnChange
        expChanges = [col(0, 1),
                      col(1, 1),
                      col(2, 1),
                      col(3, 1),
                      cell(0, 0),
                      cell(0, 1),
                      cell(1, 0),
                      cell(1, 1),
                      cell(1, 2),
                      cell(2, 0),
                      cell(2, 1)]
        changes = boardgen._enumerate_one_cell_changes(b, (10, 10))
        self._assertChanges(changes, expChanges)

    def _assertChanges(self, changes, expChanges):
        self.assertEqual(len(changes), len(expChanges))
        for change in changes:
            self.assert_(change in expChanges)
        for change in expChanges:
            self.assert_(change in changes)


class TestMakeChange(unittest.TestCase):
    def testCol1(self):
        before = ""
        change = boardgen._InsertColumnChange(0, 1)
        after = """*"""
        self._assertMakeChange(before, change, after)

    def testCol2(self):
        before = """1"""
        change = boardgen._InsertColumnChange(0, 1)
        after = """*1"""
        self._assertMakeChange(before, change, after)

    def testCol3(self):
        before = """1
                    1"""
        change = boardgen._InsertColumnChange(1, 1)
        after = """1.
                   1*"""
        self._assertMakeChange(before, change, after)

    def testCol4(self):
        before = """1
                    1"""
        change = boardgen._InsertColumnChange(2, 3)
        after = """..*
                   1.*
                   1.*"""
        self._assertMakeChange(before, change, after)

    def testCol5(self):
        before = """.1.3
                    2113"""
        change = boardgen._InsertColumnChange(2, 2)
        after = """.1*.3
                   21*13"""
        self._assertMakeChange(before, change, after)

    def testCell1(self):
        before = ""
        change = boardgen._InsertCellChange(0, 0)
        after = "*"
        self._assertMakeChange(before, change, after)

    def testCell2(self):
        before = """1"""
        change = boardgen._InsertCellChange(0, 0)
        after =  """1
                    *"""
        self._assertMakeChange(before, change, after)

    def testCell3(self):
        before = """1"""
        change = boardgen._InsertCellChange(0, 1)
        after =  """*
                    1"""
        self._assertMakeChange(before, change, after)

    def testCell4(self):
        before = """1
                    2
                    3
                    *
                    4
                    5"""
        change = boardgen._InsertCellChange(0, 1)
        after  = """1
                    2
                    3
                    4
                    *
                    *
                    5"""
        self._assertMakeChange(before, change, after)

    def testCell5(self):
        before = """1
                    2
                    3
                    *
                    4
                    5"""
        change = boardgen._InsertCellChange(0, 2)
        after  = """1
                    2
                    3
                    *
                    *
                    4
                    5"""
        self._assertMakeChange(before, change, after)

    def testCell6(self):
        before = """1
                    2
                    3
                    *
                    4
                    5"""
        change = boardgen._InsertCellChange(0, 3)
        after  = """1
                    2
                    3
                    *
                    *
                    4
                    5"""
        self._assertMakeChange(before, change, after)

    def testCell7(self):
        before = """1
                    2
                    3
                    *
                    4
                    5"""
        change = boardgen._InsertCellChange(0, 4)
        after  = """1
                    2
                    *
                    3
                    *
                    4
                    5"""
        self._assertMakeChange(before, change, after)

    def testCell8(self):
        before = """1
                    *
                    *
                    *
                    *
                    5"""
        change = boardgen._InsertCellChange(0, 0)
        after  = """1
                    5
                    *
                    *
                    *
                    *
                    *"""
        self._assertMakeChange(before, change, after)

    def _assertMakeChange(self, before, change, after):
        b = _make_board(before)
        expBoard = _make_board(after)
        boardgen._make_change(b, change)
        self.assertEqual(b, expBoard)


class TestChangeIsColorable(unittest.TestCase):
    def test1(self):
        b = _make_board("""""")
        change = boardgen._InsertCellChange(0, 0)
        self.assert_(boardgen._change_is_colorable(b, change, 1))

    def test2(self):
        b = _make_board("""1""")
        change = boardgen._InsertCellChange(0, 0)
        self.failIf(boardgen._change_is_colorable(b, change, 1))

    def test3(self):
        b = _make_board("""1""")
        change = boardgen._InsertCellChange(0, 0)
        self.assert_(boardgen._change_is_colorable(b, change, 2))

    def test4(self):
        b = _make_board("""1.2
                           1*3""")
        change = boardgen._InsertCellChange(1, 0)
        self.failIf(boardgen._change_is_colorable(b, change, 2))

    def test5(self):
        b = _make_board("""1.2
                           1*3""")
        change = boardgen._InsertCellChange(1, 0)
        self.failIf(boardgen._change_is_colorable(b, change, 3))


class TestGetCellChanges(unittest.TestCase):

    def test1(self):
        s = """"""
        expChanges = []
        self._assertCellChanges(s, expChanges, (0, 0))

    def test2(self):
        s = """1"""
        expChanges = []
        self._assertCellChanges(s, expChanges, (1, 2))

    def test3(self):
        s = """*"""
        expChanges = [boardgen._InsertCellChange(0, 1)]
        self._assertCellChanges(s, expChanges, (1, 2))

    def test4(self):
        s = """.**
               12*"""
        expChanges = [boardgen._InsertCellChange(0, 1),
                      boardgen._InsertCellChange(1, 0),
                      boardgen._InsertCellChange(1, 2),
                      boardgen._InsertCellChange(2, 2)]
        self._assertCellChanges(s, expChanges, (3, 3))

    def test5(self):
        s = """.*.
               .1.
               111"""
        expChanges = [boardgen._InsertCellChange(1, 1),
                      boardgen._InsertCellChange(1, 3)]
        self._assertCellChanges(s, expChanges, (3, 4))

    def _assertCellChanges(self, s, expChanges, board_size):
        b = _make_board(s)
        (h_changes, v_changes) = boardgen._get_cell_changes(b, board_size)
        changes = h_changes + v_changes
        print changes
        self.assertEqual(len(changes), len(expChanges))
        for change in changes:
            self.assert_(change in expChanges)
        for change in expChanges:
            self.assert_(change in changes)


class TestGetColChanges(unittest.TestCase):

    def test1(self):
        s = """"""
        expChanges = []
        self._assertCellChanges(s, expChanges, (2, 2))

    def test2(self):
        s = """1.
               12"""
        expChanges = []
        self._assertCellChanges(s, expChanges, (3, 3))

    def test3(self):
        s = """*.
               12"""
        expChanges = [boardgen._InsertColumnChange(0, 2),
                      boardgen._InsertColumnChange(1, 2)]
        self._assertCellChanges(s, expChanges, (3, 3))

    def test4(self):
        s = """*.
               **"""
        expChanges = [boardgen._InsertColumnChange(0, 2),
                      boardgen._InsertColumnChange(1, 2),
                      boardgen._InsertColumnChange(2, 1)]
        self._assertCellChanges(s, expChanges, (3, 3))

    def _assertCellChanges(self, s, expChanges, board_size):
        b = _make_board(s)
        changes = boardgen._get_col_changes(b, board_size)
        self.assertEqual(len(changes), len(expChanges))
        for change in changes:
            self.assert_(change in expChanges)
        for change in expChanges:
            self.assert_(change in changes)


def _make_board(s):
    b = board.Board()
    # Constructs a board using the given string.
    lines = [x.strip() for x in s.strip().splitlines()]

    if len(lines) == 0:
        return b

    # Make sure all lines are the same length.
    lens = [len(x) for x in lines]
    assert len(set(lens)) == 1

    val_map = {'.': None, '*': -1}
    for i in range(1, 9 + 1):
        val_map[str(i)] = i

    for (i, line) in enumerate(reversed(lines)):
        for (j, ch) in enumerate(line):
            b.set_value(j, i, val_map[ch])

    return b

if __name__ == '__main__':
    unittest.main()
