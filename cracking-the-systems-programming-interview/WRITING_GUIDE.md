# Writing guide for this book

Read this file, and `../anti_ai_slop.md`, before writing or editing any chapter.

## 1. The reader (minimally qualified reader)

The reader has written small Rust programs. They know `fn`, `let`, `if`, `match`, `struct`, `enum`,
`Vec`, `String`, and have met ownership and borrowing in *The Rust Programming Language*. They have not
used lifetimes in their own signatures, trait implementations like `TryFrom`, `Rc`, `Arc`, atomics,
`unsafe`, or async. They know what a file and a process are, but not what a cache line, a page fault, or
epoll is.

After the book, the reader can build data structures, concurrency primitives, and network servers in
Rust, measure them, and explain what the machine does while they run.

## 2. Procedure for every section

1. **Facts first.** Before prose, list the facts the section must teach. Each fact gets one concrete
   example or one step.
2. **Expand each fact into a short paragraph.** Sentence one states the fact. Sentence two gives the
   example or step. Sentence three states a constraint, a consequence, or the link to the previous
   paragraph. Keep sentences under 20 words where the content allows.
3. **Deletion pass.** List every sentence that can be deleted without losing a fact, step, definition,
   example, or constraint. Delete it. Run `python3 tools/lint_prose.py <file>` and fix every finding.
4. **Specific reader, specific action.** Each section states what the reader can do after reading it.

Every sentence must do one of: define a term, give a step, show an example, state a constraint, or
connect to the previous sentence.

## 3. Chapter shape

1. Open with where the chapter sits in the book and what the reader will build. Name the terms it
   introduces and define them before use.
2. Build intuition before code: the problem in plain words, a diagram, a small example worked by hand,
   and a memory-layout picture where memory matters to the result.
3. Introduce the code in small excerpts, one idea each. New Rust syntax is explained in plain words
   before the code that uses it.
4. End the chapter's project with the complete program, including `main`, as one listing (or one per
   file), with the command to run it and its real output.
5. Close with a short summary list of what the chapter taught and one sentence on what the next chapter
   covers, then exercises.
6. Link sections: "As you saw in section 3.2 ...", "Section 5.4 uses this ...". Only when the link
   carries information.

## 4. Style (after Manning and O'Reilly author guidance)

- Write for one reader, as if speaking to them. Address the reader as "you" and the author as "I".
- Orient before instructing. Define terms and conventions before using them. If the reader has to jump
  ahead to understand a step, the order is wrong.
- Active voice, action verbs, plain words. No unnecessary complication.
- Use NOTE:, TIP:, and WARNING: callouts for side information. Use lists and small tables.
- Write ethically: do not hide unfavorable results, do not exaggerate favorable ones, no false
  implications.
- The deletion test: if a sentence can be deleted without losing information, delete it.

## 5. Never write

Everything listed in `../anti_ai_slop.md`, plus:

- "why it matters", "what matters", "the key", "the point", "worth", "important", "crucial",
  "powerful", "elegant", "simply", "just", "note that", "interestingly", "surprisingly"
- dramatic one-line setups before an ordinary statement
- sentences about the repository, the files' history, commit dates, or the author's process
- anything about interviews, interviewers, or job applications
- nitpicks about unused imports or typos in the code
- employer or product names from the author's job search

## 6. Target style sample

This paragraph shows the target sentence length and tone.

> A `Vec<T>` stores its elements in one block of heap memory. The vector itself is three words on the
> stack: a pointer to the block, the number of elements, and the capacity of the block. When you push an
> element and the block is full, the vector allocates a larger block, copies the elements, and frees the
> old one. This is why a reference into a vector cannot be held across a `push`. The compiler rejects
> such code because the push may move every element.

## 7. Animations

Read `tools/ANIMATIONS.md` before adding or changing an animation. Animations are smooth
motion built with `tools/motion.py`, not keyframe slides, and they target the HTML edition.
The print edition needs a different treatment, described there.
