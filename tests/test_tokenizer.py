import unittest

from bashlex import tokenizer, state, flags, errors

from bashlex.tokenizer import token as t
from bashlex.tokenizer import tokentype as tt

tokenize = lambda s: list(tokenizer.tokenizer(s, state.parserstate()))

hasdollarset = set([flags.word.HASDOLLAR])

class test_tokenizer(unittest.TestCase):
    def assertTokens(self, s, tokens):
        result = tokenize(s)

        # pop the last token if it's a new line since that gets appended
        # to the input string by default and we don't really care about
        # that here
        if result[-1].value == '\n':
            result.pop()

        self.assertEquals(result, tokens)

        for t in tokens:
            self.assertEquals(str(t.value), s[t.lexpos:t.endlexpos])

    def test_empty_string(self):
        self.assertEquals(len(tokenize('')), 0)

    def test_simple(self):
        s = 'a b'
        self.assertTokens(s, [
                          t(tt.WORD, 'a', [0, 1]),
                          t(tt.WORD, 'b', [2, 3])])

    def test_meta(self):
        s = '!&()<>;&;;&;; |<<-<< <<<>>&&||<&>&<>>|&> &>>|&'
        self.assertTokens(s, [
                          t(tt.BANG, '!', [0, 1]),
                          t(tt.AMPERSAND, '&', [1, 2]),
                          t(tt.LEFT_PAREN, '(', [2, 3]),
                          t(tt.RIGHT_PAREN, ')', [3, 4]),
                          t(tt.LESS_GREATER, '<>', [4, 6]),
                          t(tt.SEMI_AND, ';&', [6, 8]),
                          t(tt.SEMI_SEMI_AND, ';;&', [8, 11]),
                          t(tt.SEMI_SEMI, ';;', [11, 13]),
                          t(tt.BAR, '|', [14, 15]),
                          t(tt.LESS_LESS_MINUS, '<<-', [15, 18]),
                          t(tt.LESS_LESS, '<<', [18, 20]),
                          t(tt.LESS_LESS_LESS, '<<<', [21, 24]),
                          t(tt.GREATER_GREATER, '>>', [24, 26]),
                          t(tt.AND_AND, '&&', [26, 28]),
                          t(tt.OR_OR, '||', [28, 30]),
                          t(tt.LESS_AND, '<&', [30, 32]),
                          t(tt.GREATER_AND, '>&', [32, 34]),
                          t(tt.LESS_GREATER, '<>', [34, 36]),
                          t(tt.GREATER_BAR, '>|', [36, 38]),
                          t(tt.AND_GREATER, '&>', [38, 40]),
                          t(tt.AND_GREATER_GREATER, '&>>', [41, 44]),
                          t(tt.BAR_AND, '|&', [44, 46])])

        s = '<&-'
        self.assertTokens(s, [
                          t(tt.LESS_AND, '<&', [0, 2]),
                          t(tt.DASH, '-', [2, 3])])

    def test_comment(self):
        s = '|# foo bar\n'
        self.assertTokens(s, [
                          t(tt.BAR, '|', [0, 1])])

    def test_shellquote(self):
        s = '"foo"'
        self.assertTokens(s, [
                          t(tt.WORD, '"foo"', [0, 5], set([flags.word.QUOTED]))])

        s = '"foo"bar\'baz\''
        self.assertTokens(s, [
                          t(tt.WORD, s, [0, len(s)], set([flags.word.QUOTED]))])

        self.assertRaises(tokenizer.MatchedPairError,
                          tokenize,
                          "'a")

    def test_shellexp(self):
        s = '<(foo) bar $(baz) ${a}'
        self.assertTokens(s, [
                          t(tt.WORD, '<(foo)', [0, 6], hasdollarset),
                          t(tt.WORD, 'bar', [7, 10]),
                          t(tt.WORD, '$(baz)', [11, 17], hasdollarset),
                          t(tt.WORD, '${a}', [18, 22], hasdollarset)])

        s = '$"foo" $1'
        self.assertTokens(s, [
                          t(tt.WORD, '$"foo"', [0, 6], set([flags.word.QUOTED])),
                          t(tt.WORD, '$1', [7, 9], hasdollarset)])

    def test_readtokenword(self):
        s = 'a\\"'
        self.assertTokens(s, [
                          t(tt.WORD, 'a\\"', [0, len(s)], set([flags.word.QUOTED]))])

    def test_parameter_expansion(self):
        # s = 'a $"foo"'
        # tok = tokenizer.tokenizer(s, state.parserstate())
        # self.assertEquals(list(tok), [t(tt.WORD, 'a'),
        #                               t(tt.WORD, '"foo"', flags=set([flags.word.QUOTED]))])

        s = 'a $$'
        self.assertTokens(s, [
                          t(tt.WORD, 'a', [0, 1]),
                          t(tt.WORD, '$$', [2, 4], hasdollarset)])

    def test_comsub(self):
        s = 'a $(b)'
        self.assertTokens(s, [
                          t(tt.WORD, 'a', [0, 1]),
                          t(tt.WORD, '$(b)', [2, 6], hasdollarset)])

        s = '$("a")'
        self.assertTokens(s, [
                          t(tt.WORD, '$("a")', [0, 6], hasdollarset)])

        s = "$($'a')"
        self.assertTokens(s, [
                          t(tt.WORD, "$($'a')", [0, 7], hasdollarset)])

        s = '$(a $(b))'
        self.assertTokens(s, [
                          t(tt.WORD, '$(a $(b))', [0, 9], hasdollarset)])

        s = '$(a ${b})'
        self.assertTokens(s, [
                          t(tt.WORD, '$(a ${b})', [0, 9], hasdollarset)])

        s = '$(a $[b])'
        self.assertTokens(s, [
                          t(tt.WORD, '$(a $[b])', [0, 9], hasdollarset)])

        s = '"$(a)"'
        self.assertTokens(s, [
                          t(tt.WORD, '"$(a)"', [0, 6], set([flags.word.HASDOLLAR,
                                                            flags.word.QUOTED]))])

        s = 'a $(! b)'
        self.assertTokens(s, [
                          t(tt.WORD, 'a', [0, 1]),
                          t(tt.WORD, '$(! b)', [2, 8], hasdollarset)])

        s = '$(!|!||)'
        self.assertTokens(s, [
                          t(tt.WORD, '$(!|!||)', [0, 8], hasdollarset)])

        s = '$(a <<EOF)'
        self.assertTokens(s, [
                          t(tt.WORD, '$(a <<EOF)', [0, 10], hasdollarset)])

        s = '$(a <b)'
        self.assertTokens(s, [
                          t(tt.WORD, '$(a <b)', [0, 7], hasdollarset)])

        s = '$(case ;; esac)'
        self.assertTokens(s, [
                          t(tt.WORD, '$(case ;; esac)', [0, 15], hasdollarset)])

        s = '$(case a in (b) c ;; (d) e ;; esac)'
        self.assertTokens(s, [
                          t(tt.WORD, '$(case a in (b) c ;; (d) e ;; esac)',
                            [0, len(s)], hasdollarset)])

        s = '$(do )'
        self.assertTokens(s, [
                          t(tt.WORD, '$(do )', [0, len(s)], hasdollarset)])

        s = '$((a))'
        self.assertTokens(s, [
                          t(tt.WORD, '$((a))', [0, len(s)], hasdollarset)])

        s = '$('
        self.assertRaises(tokenizer.MatchedPairError,
                          tokenize, s)

        s = '$(;'
        self.assertRaises(tokenizer.MatchedPairError,
                          tokenize, s)

        s = '$(<'
        self.assertRaises(tokenizer.MatchedPairError,
                          tokenize, s)

        s = '$(<<'
        self.assertRaises(tokenizer.MatchedPairError,
                          tokenize, s)

        s = '$(a\\b)'
        self.assertTokens(s, [
                          t(tt.WORD, '$(a\\b)', [0, len(s)], hasdollarset)])

        s = '$(a <<EOF\nb\nEOF)'
        self.assertTokens(s, [
                          t(tt.WORD, '$(a <<EOF\nb\nEOF)', [0, len(s)],
                            hasdollarset)])

        s = '$(a <<EOF\nb\nEOF\n)'
        self.assertTokens(s, [
                          t(tt.WORD, '$(a <<EOF\nb\nEOF\n)', [0, len(s)],
                            hasdollarset)])

        s = '$(a <<-EOF\nb\nEOF)'
        self.assertTokens(s, [
                          t(tt.WORD, '$(a <<-EOF\nb\nEOF)', [0, len(s)],
                            hasdollarset)])

        s = '$(a # comment\n)'
        self.assertTokens(s, [
                          t(tt.WORD, '$(a # comment\n)', [0, len(s)],
                            hasdollarset)])

    def test_parsematchedpair(self):
        s = '"`foo`"'
        self.assertTokens(s, [
                          t(tt.WORD, '"`foo`"', [0, len(s)], set([flags.word.QUOTED]))])

        s = '"${a}"'
        self.assertTokens(s, [
                          t(tt.WORD, '"${a}"', [0, len(s)], set([flags.word.HASDOLLAR,
                                                                flags.word.QUOTED]))])

        s = '${\'a\'}'
        self.assertTokens(s, [
                          t(tt.WORD, '${\'a\'}', [0, len(s)], hasdollarset)])

        s = '${$\'a\'}'
        self.assertTokens(s, [
                          t(tt.WORD, '${$\'a\'}', [0, len(s)], hasdollarset)])

        s = "'a\\'"
        self.assertTokens(s, [
                          t(tt.WORD, "'a\\'", [0, len(s)], set([flags.word.QUOTED]))])

        #s = '"\\\n"'
        #self.assertEquals(tokenize(s), [
        #                  t(tt.WORD, '"\\a"', flags=set([flags.word.QUOTED]))])

    def test_assignment(self):
        s = 'a=b'
        self.assertTokens(s, [
                          t(tt.ASSIGNMENT_WORD, 'a=b', [0, 3],
                            flags=set([flags.word.NOSPLIT, flags.word.ASSIGNMENT]))])

        s = 'a+=b'
        self.assertTokens(s, [
                          t(tt.ASSIGNMENT_WORD, 'a+=b', [0, 4],
                            flags=set([flags.word.NOSPLIT, flags.word.ASSIGNMENT]))])

    def test_plus_at_end_of_word(self):
        s = 'a+ b'
        self.assertTokens(s, [
                          t(tt.WORD, 'a+', [0, 2]),
                          t(tt.WORD, 'b', [3, 4])])

    def test_heredoc(self):
        s = 'a <<EOF'
        self.assertTokens(s, [
                          t(tt.WORD, 'a', [0, 1]),
                          t(tt.LESS_LESS, '<<', [2, 4]),
                          t(tt.WORD, 'EOF', [4, 7])])

    def test_herestring(self):
        s = 'a <<<foo'
        self.assertTokens(s, [
                          t(tt.WORD, 'a', [0, 1]),
                          t(tt.LESS_LESS_LESS, '<<<', [2, 5]),
                          t(tt.WORD, 'foo', [5, 8])])

        s = 'a <<<"b\nc"'
        self.assertTokens(s, [
                          t(tt.WORD, 'a', [0, 1]),
                          t(tt.LESS_LESS_LESS, '<<<', [2, 5]),
                          t(tt.WORD, '"b\nc"', [5, 10], set([flags.word.QUOTED]))])

    def test_foo(self):
        s = 'c)'
        self.assertTokens(s, [
                          t(tt.WORD, 'c', [0, 1]),
                          t(tt.RIGHT_PAREN, ')', [1, 2])])

    def test_redirections(self):
        s = '1>'
        self.assertTokens(s, [
                          t(tt.NUMBER, 1, [0, 1]),
                          t(tt.GREATER, '>', [1, 2])])
        s = '$<$(b)'
        self.assertTokens(s, [
                          t(tt.WORD, '$', [0, 1], hasdollarset),
                          t(tt.LESS, '<', [1, 2]),
                          t(tt.WORD, '$(b)', [2, 6], hasdollarset)])

    def test_quote_error(self):
        s = "a 'b"
        msg = "EOF.*matching \"'\" \\(position 4"
        self.assertRaisesRegexp(errors.ParsingError, msg, tokenize, s)

    def test_escape_error(self):
        return # TODO

        s = "a b\\"

        self.assertRaisesRegexp(errors.ParsingError, "No escaped character.*position 2", tokenize, s)

    def test_tokenize(self):
        s = 'bar -x'
        self.assertTokens(s, [
                          t(tt.WORD, 'bar', [0, 3]),
                          t(tt.WORD, '-x', [4, 6])])

        s = 'wx    y =z '
        self.assertTokens(s, [
                          t(tt.WORD, 'wx', [0, 2]),
                          t(tt.WORD, 'y', [6, 7]),
                          t(tt.WORD, '=z', [8, 10])])

        s = "a 'b' c"
        self.assertTokens(s, [
                          t(tt.WORD, 'a', [0, 1]),
                          t(tt.WORD, "'b'", [2, 5], set([flags.word.QUOTED])),
                          t(tt.WORD, 'c', [6, 7])])

        s = "a 'b  ' c"
        self.assertTokens(s, [
                          t(tt.WORD, 'a', [0, 1]),
                          t(tt.WORD, "'b  '", [2, 7], set([flags.word.QUOTED])),
                          t(tt.WORD, 'c', [8, 9])])
