// Command gpuusage reports, for every node in the cluster, how many
// nvidia.com/gpu units the node advertises, how many are held by pods, and
// which pods hold them. It is a read-only client: it lists nodes and pods
// through the API server and does the accounting itself, the same way the
// scheduler counts extended resources.
//
// Run it from code/go, against the cluster in the current kubeconfig context,
// with:
//
//	go run ./gpuusage
package main

import (
	"cmp"
	"context"
	"fmt"
	"os"
	"slices"
	"text/tabwriter"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	ctrl "sigs.k8s.io/controller-runtime"
)

// gpu is the extended resource that the NVIDIA device plugin advertises.
const gpu corev1.ResourceName = "nvidia.com/gpu"

// holder is a pod that holds GPU units on a node.
type holder struct {
	// pod is the pod's namespace and name, as "namespace/name".
	pod string
	// units is the number of nvidia.com/gpu units the pod holds.
	units int64
}

// podGPUs returns the number of GPU units a pod requests: the sum of the
// nvidia.com/gpu limits of its containers.
func podGPUs(pod *corev1.Pod) int64 {
	var units int64
	for _, c := range pod.Spec.Containers {
		if q, ok := c.Resources.Limits[gpu]; ok {
			units += q.Value()
		}
	}
	return units
}

// holdsResources reports whether a pod currently holds its resources on a
// node. A pod holds them from the moment it is bound to a node until it
// finishes; a pod that has succeeded or failed gives them back.
func holdsResources(pod *corev1.Pod) bool {
	finished := pod.Status.Phase == corev1.PodSucceeded || pod.Status.Phase == corev1.PodFailed
	return pod.Spec.NodeName != "" && !finished
}

// main runs the report and exits with status 1 on any error.
func main() {
	if err := run(context.Background()); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

// run lists every node and every pod, groups the GPU-holding pods by node,
// and prints one table row per node followed by the pods that hold its units.
func run(ctx context.Context) error {
	clientset, err := kubernetes.NewForConfig(ctrl.GetConfigOrDie())
	if err != nil {
		return err
	}
	nodes, err := clientset.CoreV1().Nodes().List(ctx, metav1.ListOptions{})
	if err != nil {
		return err
	}
	pods, err := clientset.CoreV1().Pods(metav1.NamespaceAll).List(ctx, metav1.ListOptions{})
	if err != nil {
		return err
	}

	holders := map[string][]holder{}
	for i := range pods.Items {
		pod := &pods.Items[i]
		if units := podGPUs(pod); units > 0 && holdsResources(pod) {
			name := pod.Namespace + "/" + pod.Name
			holders[pod.Spec.NodeName] = append(holders[pod.Spec.NodeName], holder{name, units})
		}
	}

	table := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(table, "NODE\tCAPACITY\tALLOCATABLE\tIN USE\tFREE")
	for _, node := range nodes.Items {
		capacity := node.Status.Capacity[gpu]
		allocatable := node.Status.Allocatable[gpu]
		var inUse int64
		for _, h := range holders[node.Name] {
			inUse += h.units
		}
		fmt.Fprintf(table, "%s\t%d\t%d\t%d\t%d\n",
			node.Name, capacity.Value(), allocatable.Value(), inUse, allocatable.Value()-inUse)
	}
	if err := table.Flush(); err != nil {
		return err
	}

	for _, node := range nodes.Items {
		list := holders[node.Name]
		slices.SortFunc(list, func(a, b holder) int { return cmp.Compare(a.pod, b.pod) })
		for _, h := range list {
			fmt.Printf("  %s holds %d on %s\n", h.pod, h.units, node.Name)
		}
	}
	return nil
}
