// Command msh is a small shell. It parses a command line into a pipeline of
// commands with redirections, starts each command with its descriptors
// arranged, waits for all of them, and reports the status of the last. The
// commands cd and exit are built in.
//
// Without arguments it runs a fixed script in a temporary directory. With -i
// it reads command lines from standard input.
//
// Run it from code/go with:
//
//	go run ./msh
package main

// ANCHOR: imports
import (
	"bufio"
	"errors"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
)

// ANCHOR_END: imports

// ANCHOR: parse
// A command is one stage of a pipeline: its arguments and the files that
// replace its standard input and output, when the line names any.
type command struct {
	args         []string
	input        string
	output       string
	appendOutput bool
}

var errSyntax = errors.New("syntax error")

// parse splits a line into the commands of a pipeline. Words and operators
// are separated by spaces. The operators are | < > and >>.
func parse(line string) ([]command, error) {
	pipeline := []command{{}}
	words := strings.Fields(line)

	for i := 0; i < len(words); i++ {
		current := &pipeline[len(pipeline)-1]

		switch word := words[i]; word {
		case "|":
			if len(current.args) == 0 {
				return nil, errSyntax
			}

			pipeline = append(pipeline, command{})

		case "<", ">", ">>":
			i++

			if i == len(words) {
				return nil, errSyntax
			}

			if word == "<" {
				current.input = words[i]
			} else {
				current.output, current.appendOutput = words[i], word == ">>"
			}

		default:
			current.args = append(current.args, word)
		}
	}

	if len(pipeline[len(pipeline)-1].args) == 0 {
		return nil, errSyntax
	}

	return pipeline, nil
}

// ANCHOR_END: parse

// ANCHOR: files
// redirect opens the files a command names and returns the files to use as
// its standard input and output. A nil result means "keep the default".
func redirect(c command) (input, output *os.File, err error) {
	if c.input != "" {
		input, err = os.Open(c.input)

		if err != nil {
			return nil, nil, err
		}
	}

	if c.output != "" {
		flags := os.O_WRONLY | os.O_CREATE | os.O_TRUNC

		if c.appendOutput {
			flags = os.O_WRONLY | os.O_CREATE | os.O_APPEND
		}

		output, err = os.OpenFile(c.output, flags, 0o644)

		if err != nil {
			return nil, nil, err
		}
	}

	return input, output, nil
}

// ANCHOR_END: files

// ANCHOR: launch
// launch starts every command of a pipeline and returns the commands that
// started. Command i reads from the pipe that command i-1 writes to, unless
// a redirection replaces that descriptor.
func launch(pipeline []command) []*exec.Cmd {
	var started []*exec.Cmd
	var fromPrevious *os.File

	for i, c := range pipeline {
		stdin, stdout := os.Stdin, os.Stdout
		var toNext, nextInput *os.File

		if fromPrevious != nil {
			stdin = fromPrevious
		}

		if i < len(pipeline)-1 {
			reader, writer, err := os.Pipe()

			if err != nil {
				fmt.Fprintln(os.Stderr, "msh:", err)

				break
			}

			stdout, toNext, nextInput = writer, writer, reader
		}

		input, output, err := redirect(c)

		if input != nil {
			stdin = input
		}

		if output != nil {
			stdout = output
		}

		if err == nil {
			child := exec.Command(c.args[0], c.args[1:]...)
			child.Stdin, child.Stdout, child.Stderr = stdin, stdout, os.Stderr
			err = child.Start()

			if err == nil {
				started = append(started, child)
			}
		}

		if errors.Is(err, exec.ErrNotFound) {
			fmt.Fprintf(os.Stderr, "msh: %s: command not found\n", c.args[0])
		} else if err != nil {
			fmt.Fprintln(os.Stderr, "msh:", err)
		}

		// The child has its own copies. The shell closes every descriptor it
		// opened for this command.
		for _, file := range []*os.File{input, output, toNext, fromPrevious} {
			if file != nil {
				file.Close()
			}
		}

		fromPrevious = nextInput
	}

	return started
}

// ANCHOR_END: launch

// ANCHOR: wait
// status converts a wait status to the number a shell reports: the exit
// status, or 128 plus the signal number.
func status(child *exec.Cmd) int {
	child.Wait()

	if wait, ok := child.ProcessState.Sys().(syscall.WaitStatus); ok && wait.Signaled() {
		return 128 + int(wait.Signal())
	}

	return child.ProcessState.ExitCode()
}

// run starts a pipeline, waits for every command, and returns the status of
// the last command, or 127 when the last command did not start.
func run(pipeline []command) int {
	started := launch(pipeline)
	last := 127

	for _, child := range started {
		last = status(child)
	}

	if len(started) < len(pipeline) {
		return 127
	}

	return last
}

// ANCHOR_END: wait

// ANCHOR: builtin
// A shell holds the state that outlives a command line.
type shell struct {
	last    int
	exiting bool
}

// execute runs one command line. cd and exit change the shell process
// itself, so they run inside it. Everything else runs in child processes.
func (s *shell) execute(line string) {
	pipeline, err := parse(line)

	if err != nil {
		fmt.Fprintln(os.Stderr, "msh:", err)
		s.last = 2

		return
	}

	switch first := pipeline[0]; {
	case len(pipeline) == 1 && first.args[0] == "cd" && len(first.args) == 2:
		s.last = 0

		if err := os.Chdir(first.args[1]); err != nil {
			fmt.Fprintln(os.Stderr, "msh:", err)
			s.last = 1
		}

	case len(pipeline) == 1 && first.args[0] == "exit":
		s.exiting = true

		if len(first.args) == 2 {
			s.last, _ = strconv.Atoi(first.args[1])
		}

	default:
		s.last = run(pipeline)
	}
}

// ANCHOR_END: builtin

// ANCHOR: script
// script is the demonstration that msh runs without arguments.
var script = []string{
	"seq 1 5 > numbers",
	"wc -l < numbers",
	"sort -rn < numbers | head -n 2 >> numbers",
	"paste -sd, numbers",
	"false",
	"nosuchcommand",
	"cd /",
	"pwd",
	"exit 3",
	"echo not reached",
}

// demonstrate runs the script in a new temporary directory and prints the
// status after each line.
func demonstrate() error {
	dir, err := os.MkdirTemp("", "msh")

	if err != nil {
		return err
	}

	defer os.RemoveAll(dir)

	if err := os.Chdir(dir); err != nil {
		return err
	}

	s := &shell{}

	for _, line := range script {
		fmt.Println("$", line)
		s.execute(line)

		if s.exiting {
			fmt.Printf("[the shell exits with status %d]\n", s.last)

			return nil
		}

		fmt.Printf("[status %d]\n", s.last)
	}

	return nil
}

// interact reads command lines from standard input until exit or the end of
// the input, and ends the process with the last status.
func interact() {
	s := &shell{}
	lines := bufio.NewScanner(os.Stdin)

	for !s.exiting {
		fmt.Print("msh$ ")

		if !lines.Scan() {
			break
		}

		if strings.TrimSpace(lines.Text()) != "" {
			s.execute(lines.Text())
		}
	}

	os.Exit(s.last)
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "-i" {
		interact()
	}

	if err := demonstrate(); err != nil {
		log.Fatal(err)
	}
}

// ANCHOR_END: script
