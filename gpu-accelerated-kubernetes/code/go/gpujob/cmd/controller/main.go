// Command controller is a controller for GpuJob objects. It runs each job as a
// pod that requests the job's GPUs, and reports the pod's progress in the
// job's status.
//
// Run it from code/go, against the cluster in the current kubeconfig context,
// with:
//
//	go run ./gpujob/cmd/controller
package main

import (
	"context"
	"os"
	"time"

	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	"k8s.io/apimachinery/pkg/runtime"
	corev1ac "k8s.io/client-go/applyconfigurations/core/v1"
	metav1ac "k8s.io/client-go/applyconfigurations/meta/v1"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	metricsserver "sigs.k8s.io/controller-runtime/pkg/metrics/server"

	gpujobv1 "gpuk8s/gpujob/api/v1"
)

// manager is the field manager name under which the controller writes with
// server-side apply.
const manager = "gpujob-controller"

// gpu is the extended resource through which a container requests GPUs.
const gpu corev1.ResourceName = "nvidia.com/gpu"

// desiredPod builds the pod that should exist for job, as an apply
// configuration: a partial object that lists only the fields this controller
// sets.
//
// The owner reference makes Kubernetes delete the pod together with the job,
// and it lets the controller map each pod event to the job that owns the pod.
func desiredPod(job *gpujobv1.GpuJob) *corev1ac.PodApplyConfiguration {
	gpus := corev1.ResourceList{gpu: *resource.NewQuantity(int64(job.Spec.GPUs), resource.DecimalSI)}
	container := corev1ac.Container().
		WithName("job").
		WithImage(job.Spec.Image).
		WithResources(corev1ac.ResourceRequirements().WithLimits(gpus))
	if len(job.Spec.Command) > 0 {
		container.WithCommand(job.Spec.Command...)
	}
	owner := metav1ac.OwnerReference().
		WithAPIVersion(gpujobv1.GroupVersion.String()).
		WithKind("GpuJob").
		WithName(job.Name).
		WithUID(job.UID).
		WithController(true).
		WithBlockOwnerDeletion(true)
	return corev1ac.Pod(job.Name, job.Namespace).
		WithOwnerReferences(owner).
		WithSpec(corev1ac.PodSpec().
			WithRestartPolicy(corev1.RestartPolicyNever).
			WithContainers(container))
}

// podGPUs returns the number of GPUs that an existing pod's container
// requests, read from its limits, and whether the pod has a GPU limit.
func podGPUs(pod *corev1.Pod) (int32, bool) {
	if len(pod.Spec.Containers) == 0 {
		return 0, false
	}
	quantity, ok := pod.Spec.Containers[0].Resources.Limits[gpu]
	return int32(quantity.Value()), ok
}

// GpuJobReconciler makes the cluster match each GpuJob.
type GpuJobReconciler struct {
	// Client reads objects from the manager's cache and writes to the API server.
	client.Client
}

// Reconcile makes the cluster match one job: it ensures the job's pod exists
// with the requested GPUs, and writes the pod's progress into the job's status.
func (r *GpuJobReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.Log.WithName("controller").WithValues("name", req.Name)

	var job gpujobv1.GpuJob
	if err := r.Get(ctx, req.NamespacedName, &job); err != nil {
		// A job deleted since it was queued needs nothing: its pod goes with it.
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// The resources of a pod are fixed when it is created. When the job asks
	// for a different number of GPUs, delete the pod and come back after it is gone.
	var pod corev1.Pod
	err := r.Get(ctx, req.NamespacedName, &pod)
	switch {
	case err == nil:
		if gpus, ok := podGPUs(&pod); !ok || gpus != job.Spec.GPUs {
			log.Info("GPU count changed, replacing pod")
			if err := r.Delete(ctx, &pod); client.IgnoreNotFound(err) != nil {
				return ctrl.Result{}, err
			}
			return ctrl.Result{RequeueAfter: 2 * time.Second}, nil
		}
	case !apierrors.IsNotFound(err):
		return ctrl.Result{}, err
	}

	if err := r.Apply(ctx, desiredPod(&job), client.FieldOwner(manager), client.ForceOwnership); err != nil {
		return ctrl.Result{}, err
	}

	// A pod that was just created is not in the cache yet; its zero value
	// yields the Pending phase, and the pod's creation event triggers the
	// reconcile that reports its real progress.
	status := gpujobv1.StatusFromPod(&pod, job.Generation)
	if job.Status != status {
		log.Info("status changed", "phase", status.Phase, "message", status.Message)
		patch := client.MergeFrom(job.DeepCopy())
		job.Status = status
		if err := r.Status().Patch(ctx, &job, patch); err != nil {
			return ctrl.Result{}, err
		}
	}
	// Changes to the pod trigger the next reconcile through Owns.
	return ctrl.Result{}, nil
}

// main builds a manager, registers the reconciler, and runs until Ctrl-C.
func main() {
	ctrl.SetLogger(zap.New(zap.UseDevMode(true))) // readable console output
	setup := ctrl.Log.WithName("setup")

	scheme := runtime.NewScheme()
	if err := clientgoscheme.AddToScheme(scheme); err != nil {
		setup.Error(err, "registering built-in types")
		os.Exit(1)
	}
	if err := gpujobv1.AddToScheme(scheme); err != nil {
		setup.Error(err, "registering GpuJob")
		os.Exit(1)
	}

	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
		Scheme:  scheme,
		Metrics: metricsserver.Options{BindAddress: "0"}, // no metrics endpoint
	})
	if err != nil {
		setup.Error(err, "creating manager")
		os.Exit(1)
	}

	err = ctrl.NewControllerManagedBy(mgr).
		For(&gpujobv1.GpuJob{}).
		Owns(&corev1.Pod{}).
		Complete(&GpuJobReconciler{Client: mgr.GetClient()})
	if err != nil {
		setup.Error(err, "creating controller")
		os.Exit(1)
	}

	if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		setup.Error(err, "running manager")
		os.Exit(1)
	}
}
