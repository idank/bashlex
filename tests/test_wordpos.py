import unittest

from bashlex import parser


class test_wordpos(unittest.TestCase):
    def test_quote_removed_positions(self):
        cases = [
            (r'\$X$X', '$X$X', [(2, 4)]),
            (r'\$X:$X', '$X:$X', [(3, 5)]),
            (r'$X\$X', '$X$X', [(0, 2)]),
            ('$X:$X', '$X:$X', [(0, 2), (3, 5)]),
            (r'"\$X$X"', '$X$X', [(2, 4)]),
            (r'\$X${X}', '$X${X}', [(2, 6)]),
            ('pre"fix"$X', 'prefix$X', [(6, 8)]),
            ('pre\\\n\\$X$X', 'pre$X$X', [(5, 7)]),
            ('~/"dir"/$X', '~/dir/$X', [(0, 1), (6, 8)]),
            ('pre"fix"$(echo a)', 'prefix$(echo a)', [(6, 15)]),
            ('pre"fix"`echo a`', 'prefix`echo a`', [(6, 14)]),
            ('pre"fix"<(echo a)', 'prefix<(echo a)', [(6, 15)]),
            ('pre"fix">(echo a)', 'prefix>(echo a)', [(6, 15)]),
        ]
        for source, expected_word, expected_spans in cases:
            word = parser.parsesingle('echo ' + source).parts[1]
            self.assertEqual(word.word, expected_word, source)
            self.assertEqual([part.wordpos for part in word.parts],
                             expected_spans, source)

    def test_source_positions_unchanged(self):
        word = parser.parsesingle(r'echo "\$X$X"').parts[1]
        self.assertEqual(word.pos, (5, 12))
        self.assertEqual(word.parts[0].pos, (9, 11))
        self.assertEqual(word.parts[0].wordpos, (2, 4))

    def test_nested_positions_are_local(self):
        for substitution in ['$(echo "\\$X$X")', '`echo "\\$X$X"`',
                             '<(echo "\\$X$X")', '>(echo "\\$X$X")']:
            source = 'echo pre"fix"' + substitution
            outer = parser.parsesingle(source).parts[1]
            part = outer.parts[0]
            self.assertEqual(part.wordpos, (6, 6 + len(substitution)))
            inner = part.command.parts[1]
            self.assertEqual(inner.word, '$X$X')
            self.assertEqual(inner.parts[0].wordpos, (2, 4))
            start, end = inner.parts[0].pos
            self.assertEqual(source[start:end], '$X')

    def test_assignment_positions(self):
        assignment = parser.parsesingle(r'V="\$X$X"').parts[0]
        self.assertEqual(assignment.kind, 'assignment')
        self.assertEqual(assignment.word, 'V=$X$X')
        self.assertEqual(assignment.parts[0].wordpos, (4, 6))

    def test_convertpos_retains_word_positions(self):
        word = parser.parsesingle(r'echo "\$X$X"', convertpos=True).parts[1]
        self.assertEqual(word.parts[0].s, '$X')
        self.assertEqual(word.parts[0].wordpos, (2, 4))

    def test_expansionlimit_retains_word_positions(self):
        word = parser.parsesingle('echo "$X$(echo y)"', expansionlimit=0).parts[1]
        self.assertEqual(len(word.parts), 1)
        self.assertEqual(word.parts[0].wordpos, (0, 2))

    def test_substitution_with_line_continuation(self):
        word = parser.parsesingle('pre\\\n\\$X$X').parts[0]
        start, end = word.parts[0].wordpos
        self.assertEqual(word.word[:start] + 'y' + word.word[end:], 'pre$Xy')
