# Periodic Motion Lecture Packet

This folder contains the structured PHY 104 packet for first-year engineering students beginning waves, optics, and modern physics. It has been consolidated into a single lecture structure to align with the active lecture note drafting.

## Folder Structure

```text
periodic motion/
├── .gitignore              # Ignore LaTeX build auxiliary files
├── README.md               # Folder overview and compile instructions
├── assignments/            # Assessment assignments
│   ├── conceptual_assignment.md
│   └── conceptual_assignment_key.md
├── quizzes/                # Lecture quiz questions and answer key
│   └── quiz_bank.md
└── lectures/               # Lecture slide decks and lesson plans
    └── periodic-motion/    # Unified Periodic Motion Lecture
        ├── main.tex        # Slide deck LaTeX source
        ├── main.pdf        # Compiled PDF slide deck
        ├── beamertheme_um.sty # "Understanding Motion" Beamer theme
        └── pre-class quiz.png # Pre-class quiz image
```

## Compilation Instructions

The slide deck is configured for compilation with LuaLaTeX. Navigate into the lecture's subdirectory and compile:

```powershell
cd lectures/periodic-motion
latexmk -lualatex main.tex
```

## References & Recommended Resources

*   **Textbook:** Howard Georgi, *The Physics of Waves*. A deep and symmetry-oriented approach to oscillations, vibrations, and waves. Available for free online at the [Harvard Faculty Page](https://www.physics.harvard.edu/~georgi/onenew.pdf).
*   **Online Course:** MIT OpenCourseWare (8.03), *Physics III: Vibrations and Waves*. A comprehensive supplemental resource covering periodic motion, mechanical vibrations, coupled oscillations, and wave mechanics. Available on [MIT OpenCourseWare](https://ocw.mit.edu/courses/8-03sc-physics-iii-vibrations-and-waves-fall-2016/).

