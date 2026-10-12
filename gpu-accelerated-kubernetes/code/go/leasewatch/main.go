// Command leasewatch reports when a host in the fleet namespace stops renewing
// its Lease, and when it starts again. It keeps an informer cache of the
// Leases and checks it once a second.
//
// It judges a Lease by its own clock, the way the Kubernetes node lifecycle
// controller judges node Leases: it notes the local time at which it first
// sees each new renewTime, and declares the host expired when no new
// renewTime has appeared for longer than the lease duration. The renewTime
// value itself was written with the host's clock, which may differ from ours.
//
// Run it from code/go, against the cluster in the current kubeconfig context,
// with:
//
//	go run ./leasewatch
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	coordinationv1 "k8s.io/api/coordination/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	ctrl "sigs.k8s.io/controller-runtime"
)

// namespace is the namespace whose Leases the program watches.
const namespace = "fleet"

// checkEvery is how often the program re-evaluates every Lease.
const checkEvery = time.Second

// ANCHOR: observation
// observation is what the program knows about one host's Lease.
type observation struct {
	// renewTime is the latest renewTime seen in the Lease.
	renewTime time.Time
	// observedAt is the local time at which that renewTime was first seen.
	observedAt time.Time
	// expired records whether the host has been reported as expired.
	expired bool
}

// ANCHOR_END: observation

// main runs the watcher until the process receives Ctrl-C or SIGTERM.
func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

// ANCHOR: run
// run starts an informer for Leases in the namespace, waits for its first
// list, and then checks every Lease in its cache once per checkEvery.
func run() error {
	clientset, err := kubernetes.NewForConfig(ctrl.GetConfigOrDie())

	if err != nil {
		return err
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	factory := informers.NewSharedInformerFactoryWithOptions(clientset, 0, informers.WithNamespace(namespace))
	lister := factory.Coordination().V1().Leases().Lister().Leases(namespace)
	factory.Start(ctx.Done())
	factory.WaitForCacheSync(ctx.Done())

	seen := map[string]*observation{}
	ticker := time.NewTicker(checkEvery)
	defer ticker.Stop()

	for {
		leases, err := lister.List(labels.Everything())

		if err != nil {
			return err
		}

		now := time.Now()

		for _, lease := range leases {
			check(seen, lease, now)
		}

		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
		}
	}
}

// ANCHOR_END: run

// ANCHOR: check
// check updates the observation of one Lease at local time now and prints a
// line when the host is first seen, expires, or renews again after expiring.
func check(seen map[string]*observation, lease *coordinationv1.Lease, now time.Time) {
	if lease.Spec.RenewTime == nil || lease.Spec.LeaseDurationSeconds == nil {
		return
	}

	renew := lease.Spec.RenewTime.Time
	duration := time.Duration(*lease.Spec.LeaseDurationSeconds) * time.Second
	stamp := now.Format(time.TimeOnly)

	obs, known := seen[lease.Name]

	switch {
	case !known:
		seen[lease.Name] = &observation{renewTime: renew, observedAt: now}
		fmt.Printf("%s %s seen, lease duration %s\n", stamp, lease.Name, duration)
	case !renew.Equal(obs.renewTime):
		obs.renewTime, obs.observedAt = renew, now

		if obs.expired {
			obs.expired = false
			fmt.Printf("%s %s renewing again\n", stamp, lease.Name)
		}
	case !obs.expired && now.Sub(obs.observedAt) > duration:
		obs.expired = true
		fmt.Printf("%s %s expired: no renewal seen for %s\n",
			stamp, lease.Name, now.Sub(obs.observedAt).Round(time.Second))
	}
}

// ANCHOR_END: check
