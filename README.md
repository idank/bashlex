# bashlex - Python parser for bash

bashlex is a Python port of the parser used internally by GNU bash.

For the most part it's transliterated from C, the major differences are:

1. it does not execute anything
2. it is reentrant
3. it generates a complete AST

## Usage

Installation:

  $ pip install git://github.com/idank/bashlex.git
  $ cd bashlex
  $ pip install -r requirements.txt

  $ python
  >>> import bashlex
  >>> ast = bashlex.parse('true && cat <(echo $(echo foo))')
  >>> print ast.dump()
  ListNode(pos=(0, 31), parts=[
    CommandNode(pos=(0, 4), parts=[
      WordNode(pos=(0, 4), word='true'),
    ]),
    OperatorNode(op='&&', pos=(5, 7)),
    CommandNode(pos=(8, 31), parts=[
      WordNode(pos=(8, 11), word='cat'),
      ProcesssubstitutionNode(command=
        CommandNode(pos=(14, 30), parts=[
          WordNode(pos=(14, 18), word='echo'),
          CommandsubstitutionNode(command=
            CommandNode(pos=(21, 29), parts=[
              WordNode(pos=(21, 25), word='echo'),
              WordNode(pos=(26, 29), word='foo'),
            ]), pos=(19, 30)),
        ]), pos=(12, 31)),
    ]),
  ])

It is also possible to only use the tokenizer and get similar behaviour to
shlex.split, but with support for more complex constructs such as command
substitutions:

  >>> bashlex.split('cat <(echo "a $(echo b)") | tee'')
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

## Motivation

I wrote this library for another project of mine, [explainshell](http://www.explainshell.com)
which needed a new parsing backend to support complex constructs such as
process/command substitutions.

## License

The license for this is the same as that used by GNU bash, GNU GPL v3+.
