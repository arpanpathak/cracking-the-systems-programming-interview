# Preface Notes

## Overview
The book explains how an operating system (OS) serves hardware requests (reading files, starting threads, etc.), moving from the hardware level upward.

## Target Audience
- Engineers working on systems software.
- Engineers preparing for systems interviews (e.g., page faults, mutex vs. condition variables, daemons).
- Requires proficiency in C++ or Rust (pointers, arrays, functions).

## Chapter Structure
Each chapter follows a pattern:
1. **Problem:** Identifies what fails without the mechanism.
2. **Model:** Explains the mechanism from first principles, often with diagrams.
3. **Code:** Demonstrations in C++20 and Rust (2024 edition).
4. **Summary:** Key ideas and common mistakes.

Special callout boxes:
- **Key idea:** Main result of a section.
- **Experiment:** Small changes for self-testing.
- **Watch out:** Subtle behaviors or common mistakes.

## Core Chapters
Chapters 1, 2, 7, 8, and 9 are considered the core. Other chapters can be read in various orders.

## Technical Details
- **C++:** C++20, compiled with Apple Clang 21.
- **Rust:** 2024 edition, compiled with `rustc` 1.99.
- **Platforms:** Behavior is consistent across Linux and macOS for most POSIX interfaces, though some differences (e.g., signals, service managers) are noted.

## Key Terms
- **Process:** A running program with its own address space.
- **Thread:** A sequence of instructions within a process's address space that can be scheduled independently.
- **Page:** Fixed-size blocks of virtual memory that the OS maps and protects.
