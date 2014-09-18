import os, copy

from bashlex import yacc, tokenizer, state, ast, subst, flags, errors, heredoc

def _partsspan(parts):
    return parts[0].pos[0], parts[-1].pos[1]

tokens = [e.name for e in tokenizer.tokentype]
precedence = (
    ('left', 'AMPERSAND', 'SEMICOLON', 'NEWLINE', 'EOF'),
    ('left', 'AND_AND', 'OR_OR'),
    ('right', 'BAR', 'BAR_AND')
)

def p_inputunit(p):
    '''inputunit : simple_list simple_list_terminator
                 | NEWLINE
                 | error NEWLINE
                 | EOF'''
    # XXX
    if p.lexer._parserstate & flags.parser.CMDSUBST:
        p.lexer._parserstate.add(flags.parser.EOFTOKEN)

    if isinstance(p[1], ast.node):
        p[0] = p[1]

def p_word_list(p):
    '''word_list : WORD
                 | word_list WORD'''
    if len(p) == 2:
        p[0] = [ast.node(kind='word', word=p[1], pos=p.lexspan(1))]
    else:
        p[0] = p[1]
        p[0].append(ast.node(kind='word', word=p[2], pos=p.lexspan(2)))

def p_redirection_heredoc(p):
    '''redirection : LESS_LESS WORD
                   | NUMBER LESS_LESS WORD
                   | REDIR_WORD LESS_LESS WORD
                   | LESS_LESS_MINUS WORD
                   | NUMBER LESS_LESS_MINUS WORD
                   | REDIR_WORD LESS_LESS_MINUS WORD'''
    parserobj = p.context
    assert isinstance(parserobj, _parser)

    output = ast.node(kind='word', word=p[len(p)-1], parts=[],
                      pos=p.lexspan(len(p)-1))
    if len(p) == 3:
        p[0] = ast.node(kind='redirect', input=None, type=p[1], heredoc=None,
                        output=output, pos=(p.lexpos(1), p.endlexpos(2)))
    else:
        p[0] = ast.node(kind='redirect', input=p[1], type=p[2], heredoc=None,
                        output=output, pos=(p.lexpos(1), p.endlexpos(3)))

    if p.slice[len(p)-2].ttype == tokenizer.tokentype.LESS_LESS:
        parserobj.redirstack.append((p[0], False))
    else:
        parserobj.redirstack.append((p[0], True))

def p_redirection(p):
    '''redirection : GREATER WORD
                   | LESS WORD
                   | NUMBER GREATER WORD
                   | NUMBER LESS WORD
                   | REDIR_WORD GREATER WORD
                   | REDIR_WORD LESS WORD
                   | GREATER_GREATER WORD
                   | NUMBER GREATER_GREATER WORD
                   | REDIR_WORD GREATER_GREATER WORD
                   | GREATER_BAR WORD
                   | NUMBER GREATER_BAR WORD
                   | REDIR_WORD GREATER_BAR WORD
                   | LESS_GREATER WORD
                   | NUMBER LESS_GREATER WORD
                   | REDIR_WORD LESS_GREATER WORD
                   | LESS_LESS_LESS WORD
                   | NUMBER LESS_LESS_LESS WORD
                   | REDIR_WORD LESS_LESS_LESS WORD
                   | LESS_AND NUMBER
                   | NUMBER LESS_AND NUMBER
                   | REDIR_WORD LESS_AND NUMBER
                   | GREATER_AND NUMBER
                   | NUMBER GREATER_AND NUMBER
                   | REDIR_WORD GREATER_AND NUMBER
                   | LESS_AND WORD
                   | NUMBER LESS_AND WORD
                   | REDIR_WORD LESS_AND WORD
                   | GREATER_AND WORD
                   | NUMBER GREATER_AND WORD
                   | REDIR_WORD GREATER_AND WORD
                   | GREATER_AND DASH
                   | NUMBER GREATER_AND DASH
                   | REDIR_WORD GREATER_AND DASH
                   | LESS_AND DASH
                   | NUMBER LESS_AND DASH
                   | REDIR_WORD LESS_AND DASH
                   | AND_GREATER WORD
                   | AND_GREATER_GREATER WORD'''
    if len(p) == 3:
        output = p[2]
        if p.slice[2].ttype == tokenizer.tokentype.WORD:
            output = _expandword(p.lexer, p.slice[2])
            assert len(output) == 1
            output = output[0]
        p[0] = ast.node(kind='redirect', input=None, type=p[1], heredoc=None,
                        output=output, pos=(p.lexpos(1), p.endlexpos(2)))
    else:
        output = p[3]
        if p.slice[3].ttype == tokenizer.tokentype.WORD:
            output = _expandword(p.lexer, p.slice[3])
            assert len(output) == 1
            output = output[0]
        p[0] = ast.node(kind='redirect', input=p[1], type=p[2], heredoc=None,
                        output=output, pos=(p.lexpos(1), p.endlexpos(3)))

def _expandword(tokenizer, tokenword):
    quoted = bool(tokenword.flags & flags.word.QUOTED)
    parts, expandedword = subst._expandwordinternal(tokenizer, tokenword, 0, 0, 0, 0)

    # XXX if we span te entire word, just replace it?
    if (not quoted and parts and
        (len(parts) == 1 or
        (tokenword.lexpos, tokenword.endlexpos) == _partsspan(parts))):
        return parts
    else:
        node = ast.node(kind='word', word=expandedword,
                        pos=(tokenword.lexpos, tokenword.endlexpos), parts=parts)
        return [node]

def p_simple_command_element(p):
    '''simple_command_element : WORD
                              | ASSIGNMENT_WORD
                              | redirection'''
    if isinstance(p[1], ast.node):
        p[0] = [p[1]]
        return

    p[0] = _expandword(p.lexer, p.slice[1])

def p_redirection_list(p):
    '''redirection_list : redirection
                        | redirection_list redirection'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        p[0].append(p[2])

def p_simple_command(p):
    '''simple_command : simple_command_element
                      | simple_command simple_command_element'''

    p[0] = p[1]
    if len(p) == 3:
        p[0].extend(p[2])

def p_command(p):
    '''command : simple_command
               | shell_command
               | shell_command redirection_list
               | function_def
               | coproc'''
    if isinstance(p[1], ast.node):
        p[0] = p[1]
        if len(p) == 3:
            p[0].redirects.extend(p[2])
            assert p[0].pos[0] < p[0].redirects[-1].pos[1]
            p[0].pos = (p[0].pos[0], p[0].redirects[-1].pos[1])
    else:
        p[0] = ast.node(kind='command', parts=p[1], pos=_partsspan(p[1]))

def p_shell_command(p):
    '''shell_command : for_command
                     | case_command
                     | WHILE compound_list DO compound_list DONE
                     | UNTIL compound_list DO compound_list DONE
                     | select_command
                     | if_command
                     | subshell
                     | group_command
                     | arith_command
                     | cond_command
                     | arith_for_command'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        assert False

def p_for_command(p):
    '''for_command : FOR WORD newline_list DO compound_list DONE
                   | FOR WORD newline_list LEFT_CURLY compound_list RIGHT_CURLY
                   | FOR WORD SEMICOLON newline_list DO compound_list DONE
                   | FOR WORD SEMICOLON newline_list LEFT_CURLY compound_list RIGHT_CURLY
                   | FOR WORD newline_list IN word_list list_terminator newline_list DO compound_list DONE
                   | FOR WORD newline_list IN word_list list_terminator newline_list LEFT_CURLY compound_list RIGHT_CURLY
                   | FOR WORD newline_list IN list_terminator newline_list DO compound_list DONE
                   | FOR WORD newline_list IN list_terminator newline_list LEFT_CURLY compound_list RIGHT_CURLY'''
    # XXX
    assert False, 'todo'

def p_arith_for_command(p):
    '''arith_for_command : FOR ARITH_FOR_EXPRS list_terminator newline_list DO compound_list DONE
                         | FOR ARITH_FOR_EXPRS list_terminator newline_list LEFT_CURLY compound_list RIGHT_CURLY
                         | FOR ARITH_FOR_EXPRS DO compound_list DONE
                         | FOR ARITH_FOR_EXPRS LEFT_CURLY compound_list RIGHT_CURLY'''
    assert False, 'todo'

def p_select_command(p):
    '''select_command : SELECT WORD newline_list DO list DONE
                      | SELECT WORD newline_list LEFT_CURLY list RIGHT_CURLY
                      | SELECT WORD SEMICOLON newline_list DO list DONE
                      | SELECT WORD SEMICOLON newline_list LEFT_CURLY list RIGHT_CURLY
                      | SELECT WORD newline_list IN word_list list_terminator newline_list DO list DONE
                      | SELECT WORD newline_list IN word_list list_terminator newline_list LEFT_CURLY list RIGHT_CURLY'''
    assert False, 'todo'

def p_case_command(p):
    '''case_command : CASE WORD newline_list IN newline_list ESAC
                    | CASE WORD newline_list IN case_clause_sequence newline_list ESAC
                    | CASE WORD newline_list IN case_clause ESAC'''
    assert False, 'todo'

def p_function_def(p):
    '''function_def : WORD LEFT_PAREN RIGHT_PAREN newline_list function_body
                    | FUNCTION WORD LEFT_PAREN RIGHT_PAREN newline_list function_body
                    | FUNCTION WORD newline_list function_body'''
    assert False, 'todo'

def p_function_body(p):
    '''function_body : shell_command
                     | shell_command redirection_list'''
    assert False, 'todo'

def p_subshell(p):
    '''subshell : LEFT_PAREN compound_list RIGHT_PAREN'''
    lparen = ast.node(kind='reservedword', word=p[1], pos=p.lexspan(1))
    rparen = ast.node(kind='reservedword', word=p[3], pos=p.lexspan(3))
    parts = [lparen, p[2], rparen]
    p[0] = ast.node(kind='compound', list=parts, redirects=[],
                    pos=_partsspan(parts))

def p_coproc(p):
    '''coproc : COPROC shell_command
              | COPROC shell_command redirection_list
              | COPROC WORD shell_command
              | COPROC WORD shell_command redirection_list
              | COPROC simple_command'''
    assert False, 'todo'

def p_if_command(p):
    '''if_command : IF compound_list THEN compound_list FI
                  | IF compound_list THEN compound_list ELSE compound_list FI
                  | IF compound_list THEN compound_list elif_clause FI'''
    # we currently don't distinguish the various lists that make up the
    # command, because it's not needed later on. if there will be a need
    # we can always add different nodes for elif/else.
    parts = []
    for i in range(1, len(p)):
        # compound_list
        if isinstance(p[i], ast.node):
            parts.append(p[i])
        # elif_clause
        elif isinstance(p[i], list):
            parts.extend(p[i])
        # a token
        else:
            assert isinstance(p.slice[i], tokenizer.token)
            parts.append(ast.node(kind='reservedword', word=p[i], pos=p.lexspan(i)))

    p[0] = ast.node(kind='compound',
                    redirects=[],
                    list=[ast.node(kind='if', parts=parts, pos=_partsspan(parts))],
                    pos=_partsspan(parts))

def p_group_command(p):
    '''group_command : LEFT_CURLY compound_list RIGHT_CURLY'''
    lcurly = ast.node(kind='reservedword', word=p[1], pos=p.lexspan(1))
    rcurly = ast.node(kind='reservedword', word=p[3], pos=p.lexspan(3))
    parts = [lcurly, p[2], rcurly]
    p[0] = ast.node(kind='compound', list=parts, redirects=[],
                    pos=_partsspan(parts))

def p_arith_command(p):
    '''arith_command : ARITH_CMD'''
    assert False, 'todo'

def p_cond_command(p):
    '''cond_command : COND_START COND_CMD COND_END'''
    assert False, 'todo'

def p_elif_clause(p):
    '''elif_clause : ELIF compound_list THEN compound_list
                   | ELIF compound_list THEN compound_list ELSE compound_list
                   | ELIF compound_list THEN compound_list elif_clause'''
    parts = []
    for i in range(1, len(p)):
        if isinstance(p[i], ast.node):
            parts.append(p[i])
        else:
            parts.append(ast.node(kind='reservedword', word=p[i], pos=p.lexspan(i)))
    p[0] = parts

def p_case_clause(p):
    '''case_clause : pattern_list
                   | case_clause_sequence pattern_list'''
    assert False, 'todo'

def p_pattern_list(p):
    '''pattern_list : newline_list pattern RIGHT_PAREN compound_list
                    | newline_list pattern RIGHT_PAREN newline_list
                    | newline_list LEFT_PAREN pattern RIGHT_PAREN compound_list
                    | newline_list LEFT_PAREN pattern RIGHT_PAREN newline_list'''
    assert False, 'todo'

def p_case_clause_sequence(p):
    '''case_clause_sequence : pattern_list SEMI_SEMI
                            | case_clause_sequence pattern_list SEMI_SEMI
                            | pattern_list SEMI_AND
                            | case_clause_sequence pattern_list SEMI_AND
                            | pattern_list SEMI_SEMI_AND
                            | case_clause_sequence pattern_list SEMI_SEMI_AND'''
    assert False, 'todo'

def p_pattern(p):
    '''pattern : WORD
               | pattern BAR WORD'''
    assert False, 'todo'

def p_list(p):
    '''list : newline_list list0'''
    p[0] = p[2]

def p_compound_list(p):
    '''compound_list : list
                     | newline_list list1'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        parts = p[2]
        if len(parts) > 1:
            p[0] = ast.node(kind='list', parts=parts, pos=_partsspan(parts))
        else:
            p[0] = parts[0]

def p_list0(p):
    '''list0 : list1 NEWLINE newline_list
             | list1 AMPERSAND newline_list
             | list1 SEMICOLON newline_list'''
    parts = p[1]
    if len(parts) > 1 or p.slice[2].ttype != tokenizer.tokentype.NEWLINE:
        parts.append(ast.node(kind='operator', op=p[2], pos=p.lexspan(2)))
        p[0] = ast.node(kind='list', parts=parts, pos=_partsspan(parts))
    else:
        p[0] = parts[0]

def p_list1(p):
    '''list1 : list1 AND_AND newline_list list1
             | list1 OR_OR newline_list list1
             | list1 AMPERSAND newline_list list1
             | list1 SEMICOLON newline_list list1
             | list1 NEWLINE newline_list list1
             | pipeline_command'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        # XXX newline
        p[0].append(ast.node(kind='operator', op=p[2], pos=p.lexspan(2)))
        p[0].extend(p[len(p) - 1])

def p_simple_list_terminator(p):
    '''simple_list_terminator : NEWLINE
                              | EOF'''
    pass

def p_list_terminator(p):
    '''list_terminator : NEWLINE
                       | SEMICOLON
                       | EOF'''
    if p[1] == ';':
        p[0] = ast.node(kind='operator', op=';')

def p_newline_list(p):
    '''newline_list : empty
                    | newline_list NEWLINE'''
    pass

def p_simple_list(p):
    '''simple_list : simple_list1
                   | simple_list1 AMPERSAND
                   | simple_list1 SEMICOLON'''
    tok = p.lexer
    heredoc.gatherheredocuments(tok)

    if len(p) == 3 or len(p[1]) > 1:
        parts = p[1]
        if len(p) == 3:
            parts.append(ast.node(kind='operator', op=p[2], pos=p.lexspan(2)))
        p[0] = ast.node(kind='list', parts=parts, pos=_partsspan(parts))
    else:
        assert len(p[1]) == 1
        p[0] = p[1][0]

    if (len(p) == 2 and p.lexer._parserstate & flags.parser.CMDSUBST and
            p.lexer._current_token.nopos() == p.lexer._shell_eof_token):
        # accept the input
        p.accept()

def p_simple_list1(p):
    '''simple_list1 : simple_list1 AND_AND newline_list simple_list1
                    | simple_list1 OR_OR newline_list simple_list1
                    | simple_list1 AMPERSAND simple_list1
                    | simple_list1 SEMICOLON simple_list1
                    | pipeline_command'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        p[0].append(ast.node(kind='operator', op=p[2], pos=p.lexspan(2)))
        p[0].extend(p[len(p) - 1])

def p_pipeline_command(p):
    '''pipeline_command : pipeline
                        | BANG pipeline_command
                        | timespec pipeline_command
                        | timespec list_terminator
                        | BANG list_terminator'''
    if len(p) == 2:
        if len(p[1]) == 1:
            p[0] = p[1][0]
        else:
            p[0] = ast.node(kind='pipeline', parts=p[1],
                            pos=(p[1][0].pos[0], p[1][-1].pos[1]))
    else:
        # XXX timespec
        node = ast.node(kind='reservedword', word='!', pos=p.lexspan(1))
        if p[2].kind == 'pipeline':
            p[0] = p[2]
            p[0].parts.insert(0, node)
            p[0].pos = (p[0].parts[0].pos[0], p[0].parts[-1].pos[1])
        else:
            p[0] = ast.node(kind='pipeline', parts=[node, p[2]],
                            pos=(node.pos[0], p[2].pos[1]))

def p_pipeline(p):
    '''pipeline : pipeline BAR newline_list pipeline
                | pipeline BAR_AND newline_list pipeline
                | command'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        p[0].append(ast.node(kind='pipe', pipe=p[2], pos=p.lexspan(2)))
        p[0].extend(p[len(p) - 1])

def p_timespec(p):
    '''timespec : TIME
                | TIME TIMEOPT
                | TIME TIMEOPT TIMEIGN'''
    assert False, 'todo'

def p_empty(p):
    '''empty :'''
    pass

def p_error(p):
    assert isinstance(p, tokenizer.token)

    if p.ttype == tokenizer.tokentype.EOF:
        raise errors.ParsingError('unexpected EOF',
                                  p.lexer._shell_input_line,
                                  len(p.lexer._shell_input_line) - 1)
    else:
        raise errors.ParsingError('unexpected token %r' % p.value,
                                  p.lexer._shell_input_line, p.lexpos)

yaccparser = yacc.yacc(tabmodule='bashlex.parsetab',
              outputdir=os.path.dirname(__file__),
              debug=False)

yaccparser.action[45]['RIGHT_PAREN'] = -155
yaccparser.action[11]['RIGHT_PAREN'] = -148

def parse(s, strictmode=True, convertpos=False):
    p = _parser(s, strictmode=strictmode, convertpos=convertpos)
    return p.parse()

class _parser(object):
    '''
    this class is mainly used to provide context to the productions
    when we're in the middle of parsing. as a hack, we shove it into the
    YaccProduction context attribute to make it accessible.
    '''
    def __init__(self, s, strictmode=True, convertpos=False, tokenizerargs=None):
        # when strictmode is set to False, we will:
        #
        # - skip reading a heredoc if we're at the end of the input

        self.s = s
        self._strictmode = strictmode
        self._convertpos = convertpos

        if tokenizerargs is None:
            tokenizerargs = {}
        self.parserstate = tokenizerargs.pop('parserstate', state.parserstate())

        self.tok = tokenizer.tokenizer(s,
                                       parserstate=self.parserstate,
                                       strictmode=strictmode,
                                       **tokenizerargs)

        self.redirstack = self.tok.redirstack

    def parse(self):
        try:
            # yacc.yacc returns a parser object that is not reentrant, it has
            # some mutable state. we make a shallow copy of it so no
            # state spills over to the next call to parse on it
            theparser = copy.copy(yaccparser)
            tree = theparser.parse(lexer=self.tok, context=self)
        except tokenizer.MatchedPairError, e:
            raise errors.ParsingError(e.args[1], self.s, len(self.s) - 1)

        if self._convertpos:
            ast.posconverter(self.s).visit(tree)
        return tree
