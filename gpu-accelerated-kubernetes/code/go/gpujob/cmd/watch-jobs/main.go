// Command watch-jobs prints the events that an informer delivers for GpuJob
// objects in the default namespace: the initial list, one object at a time,
// and then one event per change. Stop it with Ctrl-C.
//
// Run it from code/go with:
//
//	go run ./gpujob/cmd/watch-jobs
package main

import (
	"fmt"
	"os"

	"k8s.io/apimachinery/pkg/runtime"
	toolscache "k8s.io/client-go/tools/cache"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/cache"

	gpujobv1 "gpuk8s/gpujob/api/v1"
)

// namespace is the namespace whose jobs the program watches.
const namespace = "default"

// describe formats a job as its name, GPU count, and resource version.
func describe(obj any) string {
	// A deletion that a relist discovered arrives wrapped in a tombstone.
	if tombstone, ok := obj.(toolscache.DeletedFinalStateUnknown); ok {
		obj = tombstone.Obj
	}
	job := obj.(*gpujobv1.GpuJob)
	return fmt.Sprintf("%s gpus=%d v%s", job.Name, job.Spec.GPUs, job.ResourceVersion)
}

// main starts an informer for GpuJob objects and prints one line per event.
func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

// run does the work of main and returns the first error it meets.
func run() error {
	scheme := runtime.NewScheme()
	if err := gpujobv1.AddToScheme(scheme); err != nil {
		return err
	}
	informers, err := cache.New(ctrl.GetConfigOrDie(), cache.Options{
		Scheme:            scheme,
		DefaultNamespaces: map[string]cache.Config{namespace: {}},
	})
	if err != nil {
		return err
	}
	ctx := ctrl.SetupSignalHandler()
	informer, err := informers.GetInformer(ctx, &gpujobv1.GpuJob{})
	if err != nil {
		return err
	}
	registration, err := informer.AddEventHandler(toolscache.ResourceEventHandlerDetailedFuncs{
		AddFunc: func(obj any, isInInitialList bool) {
			if isInInitialList {
				fmt.Println("  listed  ", describe(obj))
			} else {
				fmt.Println("  changed ", describe(obj))
			}
		},
		UpdateFunc: func(_, obj any) { fmt.Println("  changed ", describe(obj)) },
		DeleteFunc: func(obj any) { fmt.Println("  deleted ", describe(obj)) },
	})
	if err != nil {
		return err
	}

	fmt.Println("list started")
	go informers.Start(ctx)
	if !toolscache.WaitForCacheSync(ctx.Done(), registration.HasSynced) {
		return fmt.Errorf("informer did not sync")
	}
	fmt.Println("list complete, watching")
	<-ctx.Done()
	return nil
}
