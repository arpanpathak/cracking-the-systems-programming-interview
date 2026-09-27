// Command conflict shows the API server refusing a write with an out-of-date
// resource version. Two clients read the train job, and both write it back
// with Update. The first write succeeds and changes the version, so the second
// fails with 409 Conflict.
//
// Run it from code/go, while a GpuJob named train exists, with:
//
//	go run ./gpujob/cmd/conflict
package main

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"os"

	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	gpujobv1 "gpuk8s/gpujob/api/v1"
)

// job identifies the job that both clients read and write.
var job = client.ObjectKey{Namespace: "default", Name: "train"}

// main performs the two writes and reports how the server answered each.
func main() {
	if err := run(context.Background()); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

// run does the work of main and returns the first unexpected error.
func run(ctx context.Context) error {
	scheme := runtime.NewScheme()
	if err := gpujobv1.AddToScheme(scheme); err != nil {
		return err
	}
	c, err := client.New(ctrl.GetConfigOrDie(), client.Options{Scheme: scheme})
	if err != nil {
		return err
	}

	var first gpujobv1.GpuJob
	if err := c.Get(ctx, job, &first); err != nil {
		return err
	}
	second := first.DeepCopy()
	fmt.Printf("both clients read %s at v%s\n", job.Name, first.ResourceVersion)

	first.Spec.GPUs++
	if err := c.Update(ctx, &first); err != nil {
		return err
	}
	fmt.Printf("first write stored, now v%s\n", first.ResourceVersion)

	second.Spec.GPUs += 2
	err = c.Update(ctx, second)
	var status *apierrors.StatusError
	if errors.As(err, &status) && status.ErrStatus.Code == http.StatusConflict {
		fmt.Printf("second write refused: %d %s\n", status.ErrStatus.Code, status.ErrStatus.Message)
		return nil
	}
	return fmt.Errorf("unexpected result: %v", err)
}
