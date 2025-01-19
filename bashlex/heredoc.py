from bashlex import ast, errors
import re

def gatherheredocuments(tokenizer):
    # if we're at the end of the input and we're not strict, allow skipping
    # reading the heredoc
    while tokenizer.redirstack:
        if tokenizer._peekc() is None and not tokenizer._strictmode:
            tokenizer._shell_input_line_index += 1
            return

        redirnode, killleading = tokenizer.redirstack.pop(0)
        makeheredoc(tokenizer, redirnode, 0, killleading)


def string_quote_removal(word):
    """
    Remove surrounding quotes for heredoc token.
    Other quotes are removed from the token unless escaped.

    See definition in bash's source
    https://github.com/bminor/bash/blob/master/subst.c#L11892

    >>> string_quote_removal("EOF")
    'EOF'
    >>> string_quote_removal("'EOF'")
    'EOF'
    >>> string_quote_removal('"EOF"')
    'EOF'
    >>> string_quote_removal('HERE\\\\"DOC\\\\"')
    'HERE"DOC"'
    >>> string_quote_removal('"HERE"x"DOC"')
    'HERExDOC'
    
    """
    # remove paired quote from start and end
    quote_match = re.search("^([\"'])(.*)\\1$", word)
    if quote_match:
        word = quote_match.group(2)

    # removing unescaped quotes. assumes matching quote pairs
    # bash code would fail to parse otherwise (?)
    word = re.sub("(?<=[^\\\\])[\"']","", word)

    # escaped quotes in input become literal in returned token
    word = word.replace('\\"','"').replace("\\'","'")
    return word


def makeheredoc(tokenizer, redirnode, lineno, killleading):
    redirword = string_quote_removal(redirnode.output.word)
    document = []

    startpos = tokenizer._shell_input_line_index

    #fullline = self.tok.readline(bool(redirword.output.flags & flags.word.QUOTED))
    fullline = tokenizer.readline(False)
    while fullline:
        if killleading:
            while fullline[0] == '\t':
                fullline = fullline[1:]

        if not fullline:
            continue

        if fullline[:-1] == redirword and fullline[len(redirword)] == '\n':
            document.append(fullline[:-1])
            # document_done
            break

        document.append(fullline)
        #fullline = self.readline(bool(redirnode.flags & flags.word.QUOTED))
        fullline = tokenizer.readline(False)

    if not fullline:
        raise errors.ParsingError("here-document at line %d delimited by end-of-file (wanted %r)" % (lineno, redirword), tokenizer._shell_input_line, tokenizer._shell_input_line_index)

    document = ''.join(document)
    endpos = tokenizer._shell_input_line_index - 1

    assert hasattr(redirnode, 'heredoc')
    redirnode.heredoc = ast.node(kind='heredoc', value=document,
                                 pos=(startpos, endpos))

    # if the heredoc immediately follows this node, fix its end pos
    if redirnode.pos[1] + 1 == startpos:
        redirnode.pos = (redirnode.pos[0], endpos)

    return document
