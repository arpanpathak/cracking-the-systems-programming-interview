// ch03/layout.cpp: the regions of a process address space, observed from inside.
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <unistd.h>

// Initialized global: data segment.
int g_initialized = 42;
// Uninitialized global: BSS segment.
int g_uninitialized;

// Function machine code: text segment.
__attribute__((noinline)) void anchor() { asm volatile(""); }

int main() {
    int stack_local = 7;       // stack
    int* heap = new int(99);   // heap

    std::cout << "pid " << getpid() << "\n"
              << std::hex << std::uppercase
              << "text   (function)      : " << reinterpret_cast<uintptr_t>(&anchor) << "\n"
              << "data   (initialized)   : " << reinterpret_cast<uintptr_t>(&g_initialized) << "\n"
              << "bss    (uninitialized) : " << reinterpret_cast<uintptr_t>(&g_uninitialized) << "\n"
              << "heap   (new int)       : " << reinterpret_cast<uintptr_t>(heap) << "\n"
              << "stack  (local)         : " << reinterpret_cast<uintptr_t>(&stack_local) << "\n";

    delete heap;
}
