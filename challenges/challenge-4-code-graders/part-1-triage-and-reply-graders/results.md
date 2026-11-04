# Challenge 4, part 1: results

Fill in each section when you reach its checkpoint, then run `pytest challenges/challenge-4-code-graders -q`.

## Checkpoint 1: triage graders

Run `python challenges/challenge-4-code-graders/part-1-triage-and-reply-graders/grade.py --variant A` (and B) and copy the rates:

Schema pass A: (fill in)
Whole-string match A: (fill in)
Normalised match A: (fill in)
Schema pass B: (fill in)
Whole-string match B: (fill in)
Normalised match B: (fill in)

Why is the whole-string match so low when the schema pass is high? (fill in)

## Checkpoint 2: reply graders

Reply must and must not contain A: (fill in)
Reply refund days exact A: (fill in)
Reply amount within 0.01 A: (fill in)
Reply must-pass cases A: (fill in)
Reply must and must not contain B: (fill in)
Reply refund days exact B: (fill in)
Reply amount within 0.01 B: (fill in)
Reply must-pass cases B: (fill in)

## Checkpoint 3: audit, matrices, weak class

Audit: (fill in: the line audit.py printed)

Before the matrices I expected the lowest recall for A in: (fill in)

Paste the whole output of grade.py for A and for B (each starts with "Variant A, canonical v1"):

(fill in)

Weak class A: (fill in, then one sentence)
Weak class B: (fill in, then one sentence)

### Interview answer

Question: How do you know your code graders are right, and what do their numbers show?

(fill in)
