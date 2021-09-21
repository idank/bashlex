# bashlex - Python parser for bash

[![GitHub Actions status](https://github.com/idank/bashlex/workflows/Test/badge.svg)](https://github.com/idank/bashlex/actions)

bashlex is a Python port of the parser used internally by GNU bash.

For the most part it's transliterated from C, the major differences are:

1. it does not execute anything
2. it is reentrant
3. it generates a complete AST

## Installation:

    $ pip install bashlex

## Usage

    $ python
    >>> import bashlex
    >>> parts = bashlex.parse('true && cat <(echo $(echo foo))')
    >>> for ast in parts:
    ...     print ast.dump()
    ListNode(pos=(0, 31), parts=[
      CommandNode(pos=(0, 4), parts=[
        WordNode(pos=(0, 4), word='true'),
      ]),
      OperatorNode(op='&&', pos=(5, 7)),
      CommandNode(pos=(8, 31), parts=[
        WordNode(pos=(8, 11), word='cat'),
        WordNode(pos=(12, 31), word='<(echo $(echo foo))', parts=[
          ProcesssubstitutionNode(command=
            CommandNode(pos=(14, 30), parts=[
              WordNode(pos=(14, 18), word='echo'),
              WordNode(pos=(19, 30), word='$(echo foo)', parts=[
                CommandsubstitutionNode(command=
                  CommandNode(pos=(21, 29), parts=[
                    WordNode(pos=(21, 25), word='echo'),
                    WordNode(pos=(26, 29), word='foo'),
                  ]), pos=(19, 30)),
              ]),
            ]), pos=(12, 31)),
        ]),
      ]),
    ])

It is also possible to only use the tokenizer and get similar behaviour to
shlex.split, but bashlex understands more complex constructs such as command
and process substitutions:

    >>> list(bashlex.split('cat <(echo "a $(echo b)") | tee'))
    ['cat', '<(echo "a $(echo b)")', '|', 'tee']

..compared to shlex:

    >>> shlex.split('cat <(echo "a $(echo b)") | tee')
    ['cat', '<(echo', 'a $(echo b))', '|', 'tee']

The examples/ directory contains a sample script that demonstrate how to
traverse the ast to do more complicated things.

## Limitations

Currently the parser has no support for:

- arithmetic expressions $((..))
- the more complicated parameter expansions such as ${parameter#word} are taken
  literally and do not produce child nodes

## Debugging

It can be useful to debug bashlex in conjunction to GNU bash, since it's mostly
a transliteration. Comments in the code sometimes contain line references to
bash's source code, e.g. `# bash/parse.y L2626`.

    $ git clone git://git.sv.gnu.org/bash.git
    $ cd bash
    $ git checkout df2c55de9c87c2ee8904280d26e80f5c48dd6434 # commit used in
    translating the code
    $ ./configure
    $ make CFLAGS=-g CFLAGS_FOR_BUILD=-g # debug info and don't optimize
    $ gdb --args ./bash -c 'echo foo'

Useful things to look at when debugging bash:

- variables yylval, shell_input_line, shell_input_line_index
- breakpoint at `yylex` (token numbers to names is in file parser-built)
- breakpoint at `read_token_word` (corresponds to `bashlex/tokenizer._readtokenword`)
- `xparse_dolparen, expand_word_internal` (called when parsing $())

## Motivation

I wrote this library for another project of mine, [explainshell](http://www.explainshell.com)
which needed a new parsing backend to support complex constructs such as
process/command substitutions.

## Releasing a new version

Suggestion for making a release environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- `make tests`
- bump version in `setup.py`
- git tag the new commit
- run `python -m build`
- run twine upload dist/*

## License

The license for this is the same as that used by GNU bash, GNU GPL v3+.
