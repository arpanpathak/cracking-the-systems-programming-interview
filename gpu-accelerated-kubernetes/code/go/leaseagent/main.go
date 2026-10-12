// Command leaseagent keeps a Kubernetes Lease alive for one host, the way the
// kubelet keeps its node's Lease in the kube-node-lease namespace alive. Every
// two seconds it writes the Lease named after the host in the fleet namespace,
// with the current time as renewTime and a lease duration of six seconds.
// Other programs judge the host alive for as long as these renewals continue.
//
// Run it from code/go, against the cluster in the current kubeconfig context,
// with:
//
//	go run ./leaseagent gpu-host-a
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	coordinationv1ac "k8s.io/client-go/applyconfigurations/coordination/v1"
	"k8s.io/client-go/kubernetes"
	ctrl "sigs.k8s.io/controller-runtime"
)

// ANCHOR: settings
// Lease settings. The renewal interval is a third of the lease duration, so a
// host has to miss three renewals in a row before its Lease expires.
const (
	namespace     = "fleet"
	renewEvery    = 2 * time.Second
	leaseDuration = 6 // seconds
	fieldManager  = "leaseagent"
)

// ANCHOR_END: settings

// main reads the host name from the command line and renews its Lease until
// the process receives Ctrl-C or SIGTERM.
func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: leaseagent <host>")
		os.Exit(2)
	}
	if err := run(os.Args[1]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

// ANCHOR: renew
// run writes the host's Lease with server-side apply once per renewEvery.
// A renewal that fails is reported and retried at the next tick.
func run(host string) error {
	clientset, err := kubernetes.NewForConfig(ctrl.GetConfigOrDie())
	if err != nil {
		return err
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	leases := clientset.CoordinationV1().Leases(namespace)
	acquired := metav1.NewMicroTime(time.Now())
	ticker := time.NewTicker(renewEvery)
	defer ticker.Stop()
	for {
		now := metav1.NewMicroTime(time.Now())
		lease := coordinationv1ac.Lease(host, namespace).
			WithSpec(coordinationv1ac.LeaseSpec().
				WithHolderIdentity(host).
				WithLeaseDurationSeconds(leaseDuration).
				WithAcquireTime(acquired).
				WithRenewTime(now))
		_, err := leases.Apply(ctx, lease, metav1.ApplyOptions{FieldManager: fieldManager, Force: true})
		switch {
		case ctx.Err() != nil:
			return nil
		case err != nil:
			fmt.Printf("%s %s renewal failed: %v\n", now.Format(time.TimeOnly), host, err)
		default:
			fmt.Printf("%s %s renewed\n", now.Format(time.TimeOnly), host)
		}
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
		}
	}
}

// ANCHOR_END: renew
