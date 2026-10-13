// Command pipeline runs `a | b | c` the way a shell does: each command's
// standard output is the write end of a pipe, and the next command's standard
// input is the read end of the same pipe.
//
// It runs the pipelines listed in main and prints the last command's output and how each
// command terminated.
//
// Run it from code/go with:
//
//	go run ./pipeline
package main

// ANCHOR: imports
import (
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"strings"
	"syscall"
)

// ANCHOR_END: imports

// ANCHOR: start
// start runs the commands of a pipeline. Command i writes to pipe i and reads
// from pipe i-1; the first command reads /dev/null. It returns the commands
// and the read end of the last pipe.
func start(stages [][]string) ([]*exec.Cmd, *os.File, error) {
	var input *os.File
	commands := make([]*exec.Cmd, 0, len(stages))

	for _, stage := range stages {
		reader, writer, err := os.Pipe()

		if err != nil {
			return nil, nil, err
		}

		command := exec.Command(stage[0], stage[1:]...)
		command.Stdout = writer

		if input != nil {
			command.Stdin = input
		}

		err = command.Start()

		// The child holds its own copies of both ends. Closing the parent's
		// copies leaves the child's as the only ones.
		writer.Close()

		if input != nil {
			input.Close()
		}

		if err != nil {
			reader.Close()

			return nil, nil, fmt.Errorf("%s: %w", stage[0], err)
		}

		commands, input = append(commands, command), reader
	}

	return commands, input, nil
}

// ANCHOR_END: start

// ANCHOR: status
// ending waits for a command and reports how it terminated: with an exit
// status, or by a signal.
func ending(command *exec.Cmd) string {
	command.Wait()

	state := command.ProcessState

	if status, ok := state.Sys().(syscall.WaitStatus); ok && status.Signaled() {
		return fmt.Sprintf("killed by signal %d", status.Signal())
	}

	return fmt.Sprintf("exited with status %d", state.ExitCode())
}

// ANCHOR_END: status

// ANCHOR: run
// run starts a pipeline, reads the last command's output to the end of the
// stream, and prints the output and each command's termination.
func run(line string) error {
	var stages [][]string

	for _, stage := range strings.Split(line, " | ") {
		stages = append(stages, strings.Fields(stage))
	}

	commands, output, err := start(stages)

	if err != nil {
		return err
	}

	defer output.Close()

	text, err := io.ReadAll(output)

	if err != nil {
		return err
	}

	fmt.Println(line)
	fmt.Printf("  output: %s\n", strings.Join(strings.Fields(string(text)), " "))

	for i, command := range commands {
		fmt.Printf("  %s: %s\n", stages[i][0], ending(command))
	}

	return nil
}

// ANCHOR_END: run

func main() {
	for _, line := range []string{"seq 1 100000 | grep 7 | wc -l", "yes | head -n 3"} {
		if err := run(line); err != nil {
			log.Fatal(err)
		}
	}
}
