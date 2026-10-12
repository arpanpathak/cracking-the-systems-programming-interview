// Command gpuctl is a small command-line client for a GPU cluster, written to
// build and behave the same on Linux, macOS, and Windows.
//
//	gpuctl nodes [-o table|json]   list the cluster's nodes and their GPUs
//	gpuctl config                  print where gpuctl looks for its files
//	gpuctl version                 print the version and the platform
//
// Data goes to standard output and messages to standard error. The exit
// status is 0 on success, 1 when a command fails, and 2 when the command line
// is wrong.
//
// Run it from code/go with:
//
//	go run ./gpuctl nodes
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"text/tabwriter"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
)

// version is the tool's version, printed by "gpuctl version".
const version = "0.1.0"

// ANCHOR: exit
// Exit statuses. A script that calls gpuctl tells a failed command from a
// mistyped one by the status alone.
const (
	exitOK      = 0
	exitFailure = 1
	exitUsage   = 2
)

const usage = `usage:
  gpuctl nodes [-o table|json]
  gpuctl config
  gpuctl version
`

// ANCHOR_END: exit

// ANCHOR: paths
// configFile returns the path of gpuctl's own configuration file. The
// directory is the one each operating system sets aside for a user's
// settings.
func configFile() (string, error) {
	dir, err := os.UserConfigDir()

	if err != nil {
		return "", err
	}

	return filepath.Join(dir, "gpuctl", "config.toml"), nil
}

// kubeconfig returns the file that names the cluster and the credentials:
// the KUBECONFIG environment variable if it is set, and .kube/config in the
// user's home directory otherwise.
func kubeconfig() string {
	return clientcmd.NewDefaultClientConfigLoadingRules().GetDefaultFilename()
}

// ANCHOR_END: paths

// ANCHOR: nodes
// NodeInfo is one row of "gpuctl nodes".
type NodeInfo struct {
	Name    string `json:"name"`
	GPUs    int64  `json:"gpus"`
	Arch    string `json:"arch"`
	OS      string `json:"os"`
	Kubelet string `json:"kubelet"`
}

// listNodes asks the API server for every node and keeps the fields the
// command prints.
func listNodes(ctx context.Context) ([]NodeInfo, error) {
	rules := clientcmd.NewDefaultClientConfigLoadingRules()
	config, err := clientcmd.NewNonInteractiveDeferredLoadingClientConfig(rules, nil).ClientConfig()

	if err != nil {
		return nil, err
	}

	clientset, err := kubernetes.NewForConfig(config)

	if err != nil {
		return nil, err
	}

	nodes, err := clientset.CoreV1().Nodes().List(ctx, metav1.ListOptions{})

	if err != nil {
		return nil, err
	}

	rows := make([]NodeInfo, 0, len(nodes.Items))

	for _, n := range nodes.Items {
		gpus := n.Status.Allocatable["nvidia.com/gpu"]
		rows = append(rows, NodeInfo{
			Name:    n.Name,
			GPUs:    gpus.Value(),
			Arch:    n.Status.NodeInfo.Architecture,
			OS:      n.Status.NodeInfo.OperatingSystem,
			Kubelet: n.Status.NodeInfo.KubeletVersion,
		})
	}

	return rows, nil
}

// ANCHOR_END: nodes

// ANCHOR: output
// printNodes writes the rows as a table for a person or as JSON for a program.
func printNodes(out io.Writer, rows []NodeInfo, format string) error {
	if format == "json" {
		enc := json.NewEncoder(out)
		enc.SetIndent("", "  ")

		return enc.Encode(rows)
	}

	table := tabwriter.NewWriter(out, 0, 0, 2, ' ', 0)
	fmt.Fprintln(table, "NAME\tGPUS\tARCH\tOS\tKUBELET")

	for _, r := range rows {
		fmt.Fprintf(table, "%s\t%d\t%s\t%s\t%s\n", r.Name, r.GPUs, r.Arch, r.OS, r.Kubelet)
	}

	return table.Flush()
}

// ANCHOR_END: output

// ANCHOR: run
// run carries out one command line and returns the exit status. It takes its
// arguments and its two output streams as parameters, so a test can call it
// without starting a process.
func run(args []string, out, errOut io.Writer) int {
	if len(args) == 0 {
		fmt.Fprint(errOut, usage)

		return exitUsage
	}

	switch args[0] {
	case "version":
		fmt.Fprintf(out, "gpuctl %s %s/%s\n", version, runtime.GOOS, runtime.GOARCH)
	case "config":
		file, err := configFile()

		if err != nil {
			fmt.Fprintln(errOut, "gpuctl:", err)

			return exitFailure
		}

		fmt.Fprintf(out, "config file  %s\nkubeconfig   %s\n", file, kubeconfig())
	case "nodes":
		flags := flag.NewFlagSet("nodes", flag.ContinueOnError)
		flags.SetOutput(io.Discard)
		format := flags.String("o", "table", "output format: table or json")

		if err := flags.Parse(args[1:]); err != nil || (*format != "table" && *format != "json") {
			fmt.Fprint(errOut, usage)

			return exitUsage
		}

		rows, err := listNodes(context.Background())

		if err == nil {
			err = printNodes(out, rows, *format)
		}

		if err != nil {
			fmt.Fprintln(errOut, "gpuctl:", err)

			return exitFailure
		}
	default:
		fmt.Fprintf(errOut, "gpuctl: unknown command %q\n%s", args[0], usage)

		return exitUsage
	}

	return exitOK
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

// ANCHOR_END: run
