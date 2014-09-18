import unittest, functools

from bashlex import parser, state, flags, ast, errors

parse = functools.partial(parser.parse, convertpos=True)

def reservedwordnode(word, s):
    return ast.node(kind='reservedword', word=word, s=s)

def commandnode(s, *parts):
    return ast.node(kind='command', s=s, parts=list(parts))

def wordnode(word, s=None, parts=None):
    if s is None:
        s = word
    if parts is None:
        parts = []
    return ast.node(kind='word', word=word, s=s, parts=list(parts))

def parameternode(value, s):
    return ast.node(kind='parameter', value=value, s=s)

def variablenode(value, s):
    return ast.node(kind='variable', value=value, s=s)

def heredocnode(value, s=None):
    if s is None:
        s = value
    return ast.node(kind='heredoc', value=value, s=s)

def tildenode(value, s):
    return ast.node(kind='tilde', value=value, s=s)

def redirectnode(s, input, type, output, heredoc=None):
    return ast.node(kind='redirect', input=input, type=type, output=output,
                    heredoc=heredoc, s=s)

def pipenode(pipe, s):
    return ast.node(kind='pipe', pipe=pipe, s=s)

def pipelinenode(s, *parts):
    oldparts = parts
    if parts[0].kind == 'reservedword' and parts[0].word == '!':
        parts = parts[1:]
    for i in range(len(parts)):
        if i % 2 == 0:
            assert parts[i].kind in ('command', 'compound'), parts[i].kind
        else:
            assert parts[i].kind == 'pipe', parts[i].kind
    return ast.node(kind='pipeline', s=s, parts=list(oldparts))

def operatornode(op, s):
    return ast.node(kind='operator', op=op, s=s)

def listnode(s, *parts):
    for i in range(len(parts)):
        if i % 2 == 0:
            assert parts[i].kind in ('command', 'pipeline', 'compound'), parts[i].kind
        else:
            assert parts[i].kind == 'operator', parts[i].kind
    return ast.node(kind='list', parts=list(parts), s=s)

def compoundnode(s, *parts, **kwargs):
    redirects = kwargs.pop('redirects', [])
    assert not kwargs
    return ast.node(kind='compound', s=s, list=list(parts), redirects=redirects)

def procsubnode(s, command):
    return ast.node(kind='processsubstitution', s=s, command=command)

def comsubnode(s, command):
    return ast.node(kind='commandsubstitution', s=s, command=command)

def ifnode(s, *parts):
    return ast.node(kind='if', parts=list(parts), s=s)

class test_parser(unittest.TestCase):
    def assertASTEquals(self, s, expected, strictmode=True):
        result = parse(s, strictmode=strictmode)

        msg = 'ASTs not equal for %r\n\nresult:\n\n%s\n\n!=\n\nexpected:\n\n%s' % (s, result.dump(), expected.dump())
        self.assertEquals(result, expected, msg)

    def test_command(self):
        s = 'a b c'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  wordnode('b'),
                  wordnode('c')))

        s = 'a b "c"'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  wordnode('b'),
                  wordnode('c', '"c"')))

        s = '2>/dev/null a b "c"'
        self.assertASTEquals(s,
                commandnode(s,
                  redirectnode('2>/dev/null', 2, '>', wordnode('/dev/null')),
                  wordnode('a'),
                  wordnode('b'),
                  wordnode('c', '"c"')))

        s = 'a b>&1 2>&1'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  wordnode('b'),
                  redirectnode('>&1', None, '>&', 1),
                  redirectnode('2>&1', 2, '>&', 1)))

    def test_pipeline(self):
        s = 'a | b'
        self.assertASTEquals(s,
                          pipelinenode(s,
                            commandnode('a', wordnode('a')),
                            pipenode('|', '|'),
                            commandnode('b', wordnode('b'))))

        s = '! a | b'
        self.assertASTEquals(s,
                          pipelinenode(s,
                            reservedwordnode('!', '!'),
                            commandnode('a', wordnode('a')),
                            pipenode('|', '|'),
                            commandnode('b', wordnode('b'))
                          ))

    def test_list(self):
        s = 'a;'
        self.assertASTEquals(s,
                          listnode(s,
                            commandnode('a', wordnode('a')),
                            operatornode(';', ';'),
                          ))

        s = 'a && b'
        self.assertASTEquals(s,
                          listnode(s,
                            commandnode('a', wordnode('a')),
                            operatornode('&&', '&&'),
                            commandnode('b', wordnode('b'))
                          ))

        s = 'a; b; c& d'
        self.assertASTEquals(s,
                          listnode(s,
                            commandnode('a', wordnode('a')),
                            operatornode(';', ';'),
                            commandnode('b', wordnode('b')),
                            operatornode(';', ';'),
                            commandnode('c', wordnode('c')),
                            operatornode('&', '&'),
                            commandnode('d', wordnode('d'))
                          ))

        s = 'a | b && c'
        self.assertASTEquals(s,
                          listnode(s,
                            pipelinenode('a | b',
                              commandnode('a', wordnode('a')),
                              pipenode('|', '|'),
                              commandnode('b', wordnode('b'))),
                            operatornode('&&', '&&'),
                            commandnode('c', wordnode('c'))
                          ))

    def test_nestedsubs(self):
        s = '$($<$(a) b)'
        self.assertASTEquals(s,
            commandnode(s,
                comsubnode(s,
                    commandnode('$<$(a) b',
                        wordnode('$'),
                        redirectnode('<$(a)', None, '<',
                            comsubnode('$(a)',
                                commandnode('a',
                                    wordnode('a'))
                            )
                        ),
                        wordnode('b'),
                    )
                )
            )
        )

    def test_paramexpand(self):
        s = 'a $1 $foo_bar "$@ $#" ~foo " ~bar" ${a} "${}"'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  parameternode('$1', '$1'),
                  variablenode('$foo_bar', '$foo_bar'),
                  wordnode('$@ $#', '"$@ $#"', [
                      parameternode('$@', '$@'),
                      parameternode('$#', '$#')
                  ]),
                  tildenode('~foo', '~foo'),
                  wordnode(' ~bar', '" ~bar"'),
                  parameternode('${a}', '${a}'),
                  wordnode('${}', '"${}"', [
                      parameternode('${}', '${}'),
                  ]),
                )
              )

    def test_processsub(self):
        s = 'a <(b $(c))'
        self.assertASTEquals(s,
            commandnode(s,
                wordnode('a'),
                procsubnode('<(b $(c))',
                    commandnode('b $(c)',
                        wordnode('b'),
                        comsubnode('$(c)',
                            commandnode('c',
                                wordnode('c'))
                        )
                    )
                )
            )
        )

        s = 'a `b` "`c`" \'`c`\''
        self.assertASTEquals(s,
            commandnode(s,
                wordnode('a'),
                wordnode('`b`', '`b`', [
                    comsubnode('`b`',
                        commandnode('b',
                            wordnode('b'))
                    ),
                ]),
                wordnode('`c`', '"`c`"', [
                    comsubnode('`c`',
                        commandnode('c',
                            wordnode('c'))
                    ),
                ]),
                wordnode('`c`', "'`c`'")
            )
        )

    def test_error(self):
        self.assertRaises(errors.ParsingError, parse, 'a))')

    def test_redirection_input(self):
        s = 'a <f'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  redirectnode('<f', None, '<', wordnode('f'))))

        s = 'a <1'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  redirectnode('<1', None, '<', wordnode('1'))))

        s = 'a 1<f'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  redirectnode('1<f', 1, '<', wordnode('f'))))

        s = 'a 1 <f'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  wordnode('1'),
                  redirectnode('<f', None, '<', wordnode('f'))))

        s = 'a b<f'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  wordnode('b'),
                  redirectnode('<f', None, '<', wordnode('f'))))

        s = 'a 0<&3'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  redirectnode('0<&3', 0, '<&', 3)))

    def test_compound(self):
        s = '(a) && (b)'
        self.assertASTEquals(s,
                          listnode('(a) && (b)',
                            compoundnode('(a)',
                              reservedwordnode('(', '('),
                              commandnode('a',
                                wordnode('a')),
                              reservedwordnode(')', ')'),
                              ),
                            operatornode('&&', '&&'),
                            compoundnode('(b)',
                              reservedwordnode('(', '('),
                              commandnode('b',
                                wordnode('b')),
                              reservedwordnode(')', ')'),
                              ),
                          ))

        s = '(a) | (b)'
        self.assertASTEquals(s,
                          pipelinenode(s,
                            compoundnode('(a)',
                              reservedwordnode('(', '('),
                              commandnode('a',
                                wordnode('a')),
                              reservedwordnode(')', ')')),
                            pipenode('|', '|'),
                            compoundnode('(b)',
                              reservedwordnode('(', '('),
                              commandnode('b',
                                wordnode('b')),
                              reservedwordnode(')', ')')),
                          ))

        s = '(a) | (b) > /dev/null'
        self.assertASTEquals(s,
                          pipelinenode(s,
                            compoundnode('(a)',
                              reservedwordnode('(', '('),
                              commandnode('a',
                                wordnode('a')),
                              reservedwordnode(')', ')')),
                            pipenode('|', '|'),
                            compoundnode('(b) > /dev/null',
                              reservedwordnode('(', '('),
                              commandnode('b',
                                wordnode('b')),
                              reservedwordnode(')', ')'),
                              redirects=[
                                redirectnode('> /dev/null', None, '>',
                                  wordnode('/dev/null'))]),
                          ))

        s = '(a && (b; c&)) || d'
        self.assertASTEquals(s,
                listnode(s,
                  compoundnode('(a && (b; c&))',
                    reservedwordnode('(', '('),
                    listnode('a && (b; c&)',
                      commandnode('a',
                        wordnode('a')),
                      operatornode('&&', '&&'),
                      compoundnode('(b; c&)',
                        reservedwordnode('(', '('),
                        listnode('b; c&',
                          commandnode('b',
                            wordnode('b')),
                          operatornode(';', ';'),
                          commandnode('c',
                            wordnode('c')),
                          operatornode('&', '&')
                        ),
                        reservedwordnode(')', ')'),
                      ),
                    ),
                    reservedwordnode(')', ')'),
                  ),
                  operatornode('||', '||'),
                  commandnode('d',
                    wordnode('d')),
                ))

    def test_compound_redirection(self):
        s = '(a) > /dev/null'
        self.assertASTEquals(s,
                compoundnode(s,
                  reservedwordnode('(', '('),
                  commandnode('a',
                    wordnode('a')),
                  reservedwordnode(')', ')'),
                  redirects=[redirectnode('> /dev/null', None, '>', wordnode('/dev/null'))]
                ))

    def test_compound_pipe(self):
        s = '(a) | b'
        self.assertASTEquals(s,
                pipelinenode(s,
                  compoundnode('(a)',
                    reservedwordnode('(', '('),
                    commandnode('a',
                      wordnode('a')),
                    reservedwordnode(')', ')'),
                  ),
                  pipenode('|', '|'),
                  commandnode('b',
                    wordnode('b'))
                ))

    def test_group(self):
        # reserved words are recognized only at the start of a simple command
        s = 'echo {}'
        self.assertASTEquals(s,
                          commandnode(s,
                            wordnode('echo'), wordnode('{}'))
                          )

        # reserved word at beginning isn't reserved if quoted
        s = "'{' foo"
        self.assertASTEquals(s,
                          commandnode(s,
                            wordnode('{', "'{'"), wordnode('foo'))
                          )

        s = '{ a; }'
        self.assertASTEquals(s,
                          compoundnode(s,
                            reservedwordnode('{', '{'),
                            listnode('a;',
                              commandnode('a', wordnode('a')),
                              operatornode(';', ';'),
                            ),
                            reservedwordnode('}', '}'),
                          ))

        s = '{ a; b; }'
        self.assertASTEquals(s,
                          compoundnode(s,
                            reservedwordnode('{', '{'),
                            listnode('a; b;',
                              commandnode('a', wordnode('a')),
                              operatornode(';', ';'),
                              commandnode('b', wordnode('b')),
                              operatornode(';', ';')
                            ),
                            reservedwordnode('}', '}'),
                          ))

        s = '(a) && { b; }'
        self.assertASTEquals(s,
                          listnode('(a) && { b; }',
                            compoundnode('(a)',
                              reservedwordnode('(', '('),
                              commandnode('a',
                                wordnode('a')),
                              reservedwordnode(')', ')')),
                            operatornode('&&', '&&'),
                            compoundnode('{ b; }',
                              reservedwordnode('{', '{'),
                              listnode('b;',
                                commandnode('b',
                                  wordnode('b')),
                                operatornode(';', ';')),
                              reservedwordnode('}', '}'),
                              )
                          ))

        s = 'a; ! { b; }'
        self.assertASTEquals(s,
                          listnode(s,
                            commandnode('a', wordnode('a')),
                            operatornode(';', ';'),
                              pipelinenode('! { b; }',
                                reservedwordnode('!', '!'),
                                compoundnode('{ b; }',
                                  reservedwordnode('{', '{'),
                                  listnode('b;',
                                    commandnode('b', wordnode('b')),
                                    operatornode(';', ';'),
                                  ),
                                  reservedwordnode('}', '}'),
                                )
                              )
                          ))

    def test_invalid_control(self):
        s = 'a &| b'
        self.assertRaisesRegexp(errors.ParsingError, "unexpected token '|'.*position 3", parse, s)

    def test_invalid_redirect(self):
        s = 'a 2>'
        self.assertRaisesRegexp(errors.ParsingError, r"unexpected token '\\n'.*position 4", parse, s)

        s = 'ssh -p 2222 <user>@<host>'
        self.assertRaisesRegexp(errors.ParsingError, r"unexpected token '\\n'.*position %d" % len(s), parse, s)

    def test_if(self):
        s = 'if foo; then bar; fi'
        self.assertASTEquals(s,
                          compoundnode(s,
                            ifnode(s,
                              reservedwordnode('if', 'if'),
                              listnode('foo;',
                                commandnode('foo', wordnode('foo')),
                                operatornode(';', ';')),
                              reservedwordnode('then', 'then'),
                              listnode('bar;',
                                commandnode('bar', wordnode('bar')),
                                operatornode(';', ';')),
                              reservedwordnode('fi', 'fi'),
                            ))
                          )

        s = 'if foo; bar; then baz; fi'
        self.assertASTEquals(s,
                          compoundnode(s,
                            ifnode(s,
                              reservedwordnode('if', 'if'),
                              listnode('foo; bar;',
                                commandnode('foo', wordnode('foo')),
                                operatornode(';', ';'),
                                commandnode('bar', wordnode('bar')),
                                operatornode(';', ';')),
                              reservedwordnode('then', 'then'),
                              listnode('baz;',
                                commandnode('baz', wordnode('baz')),
                                operatornode(';', ';')),
                              reservedwordnode('fi', 'fi'),
                            ))
                          )

        s = 'if foo; then bar; else baz; fi'
        self.assertASTEquals(s,
                          compoundnode(s,
                            ifnode(s,
                              reservedwordnode('if', 'if'),
                              listnode('foo;',
                                commandnode('foo', wordnode('foo')),
                                operatornode(';', ';')),
                              reservedwordnode('then', 'then'),
                              listnode('bar;',
                                commandnode('bar', wordnode('bar')),
                                operatornode(';', ';')),
                              reservedwordnode('else', 'else'),
                              listnode('baz;',
                                commandnode('baz', wordnode('baz')),
                                operatornode(';', ';')),
                              reservedwordnode('fi', 'fi'),
                              ))
                          )

        s = 'if foo; then bar; elif baz; then barbaz; fi'
        self.assertASTEquals(s,
                          compoundnode(s,
                            ifnode(s,
                              reservedwordnode('if', 'if'),
                              listnode('foo;',
                                commandnode('foo', wordnode('foo')),
                                operatornode(';', ';')),
                              reservedwordnode('then', 'then'),
                              listnode('bar;',
                                commandnode('bar', wordnode('bar')),
                                operatornode(';', ';')),
                              reservedwordnode('elif', 'elif'),
                              listnode('baz;',
                                commandnode('baz', wordnode('baz')),
                                operatornode(';', ';')),
                              reservedwordnode('then', 'then'),
                              listnode('barbaz;',
                                commandnode('barbaz', wordnode('barbaz')),
                                operatornode(';', ';')),
                              reservedwordnode('fi', 'fi'),
                              ))
                          )

        s = 'if foo; then bar; elif baz; then barbaz; else foobar; fi'
        self.assertASTEquals(s,
                          compoundnode(s,
                            ifnode(s,
                              reservedwordnode('if', 'if'),
                              listnode('foo;',
                                commandnode('foo', wordnode('foo')),
                                operatornode(';', ';')),
                              reservedwordnode('then', 'then'),
                              listnode('bar;',
                                commandnode('bar', wordnode('bar')),
                                operatornode(';', ';')),
                              reservedwordnode('elif', 'elif'),
                              listnode('baz;',
                                commandnode('baz', wordnode('baz')),
                                operatornode(';', ';')),
                              reservedwordnode('then', 'then'),
                              listnode('barbaz;',
                                commandnode('barbaz', wordnode('barbaz')),
                                operatornode(';', ';')),
                              reservedwordnode('else', 'else'),
                              listnode('foobar;',
                                commandnode('foobar', wordnode('foobar')),
                                operatornode(';', ';')),
                              reservedwordnode('fi', 'fi'),
                              ))
                          )

    def test_malformed_if(self):
        s = 'if foo; bar; fi'
        self.assertRaisesRegexp(errors.ParsingError, "unexpected token 'fi'.*position 13", parse, s)

        s = 'if foo; then bar;'
        self.assertRaisesRegexp(errors.ParsingError, "unexpected EOF.*position 17", parse, s)

        s = 'if foo; then bar; elif baz; fi'
        self.assertRaisesRegexp(errors.ParsingError, "unexpected token 'fi'.*position 28", parse, s)

    def test_word_expansion(self):
        s = "'a' ' b' \"'c'\""
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a', "'a'"),
                  wordnode(' b', "' b'"),
                  wordnode("'c'", "\"'c'\"")))

        s = '"a\'b\'"'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode("a'b'", s)))

        s = "'$(a)' \"$(b)\""
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode("$(a)", "'$(a)'"),
                  wordnode("$(b)", '"$(b)"', [
                      comsubnode("$(b)",
                        commandnode("b", wordnode("b"))
                      )
                  ])))

        s = "\"$(a \"b\" 'c')\" '$(a \"b\" 'c')'"
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode("$(a \"b\" 'c')", "\"$(a \"b\" 'c')\"", [
                      comsubnode("$(a \"b\" 'c')",
                          commandnode("a \"b\" 'c'",
                              wordnode('a'),
                              wordnode('b', '"b"'),
                              wordnode('c', "'c'")
                          )
                      )
                  ]),
                  wordnode("$(a \"b\" 'c')", "'$(a \"b\" 'c')'")
                ))

    def test_escape_not_part_of_word(self):
        s = "a \\;"
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a'),
                  wordnode(';', '\\;')))

    def test_heredoc_spec(self):
        for redirect_kind in ('<<', '<<<'):
            s = 'a %sEOF | b' % redirect_kind
            self.assertASTEquals(s,
                  pipelinenode(s,
                    commandnode('a %sEOF' % redirect_kind,
                      wordnode('a', 'a'),
                      redirectnode('%sEOF' % redirect_kind, None,
                                   redirect_kind, wordnode('EOF'))),
                    pipenode('|', '|'),
                    commandnode('b', wordnode('b', 'b'))),
                  False)

        s = 'a <<-b'
        self.assertASTEquals(s,
                commandnode(s,
                  wordnode('a', 'a'),
                  redirectnode('<<-b', None, '<<-', wordnode('b'))),
                False)

        s = 'a <<<<b'
        self.assertRaisesRegexp(errors.ParsingError, "unexpected token '<'.*5", parse, s)

    def test_heredoc_with_actual_doc(self):
        doc = 'foo\nbar\nEOF'
        s = '''a <<EOF
%s''' % doc

        self.assertASTEquals(s,
                commandnode('a <<EOF',
                  wordnode('a'),
                  redirectnode('<<EOF', None, '<<', wordnode('EOF'),
                      heredocnode(doc))
                ))

        s = 'a <<EOF\nb'
        self.assertRaisesRegexp(errors.ParsingError,
                                "delimited by end-of-file \\(wanted 'EOF'",
                                parse, s)