/*
Copyright 2026 Arpan Pathak.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package controller

import (
	"context"
	"fmt"
	"maps"
	"strconv"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/equality"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log"

	gpucloudv1 "github.com/arpanpathak/gpu-cloud-operator/api/v1"
)

const (
	managedByLabel = "app.kubernetes.io/managed-by"
	workloadLabel  = "gpucloud.example.com/workload"
)

// GpuWorkloadReconciler reconciles a GpuWorkload object.
type GpuWorkloadReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=gpucloud.example.com,resources=gpuworkloads,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=gpucloud.example.com,resources=gpuworkloads/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=gpucloud.example.com,resources=gpuworkloads/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=core,resources=services,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=core,resources=pods,verbs=get;list;watch

// Reconcile makes the cluster state match the desired GpuWorkload state.
func (r *GpuWorkloadReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx).WithValues("gpuworkload", req.NamespacedName)

	workload := &gpucloudv1.GpuWorkload{}
	if err := r.Get(ctx, req.NamespacedName, workload); err != nil {
		// If the CRD is deleted, the children are removed by owner-reference GC.
		if apierrors.IsNotFound(err) {
			return ctrl.Result{}, nil
		}
		return ctrl.Result{}, err
	}

	if err := r.reconcileDeployment(ctx, workload); err != nil {
		logger.Error(err, "failed to reconcile Deployment")
		return ctrl.Result{}, err
	}

	if err := r.reconcileService(ctx, workload); err != nil {
		logger.Error(err, "failed to reconcile Service")
		return ctrl.Result{}, err
	}

	if err := r.updateStatus(ctx, workload); err != nil {
		logger.Error(err, "failed to update status")
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *GpuWorkloadReconciler) reconcileDeployment(ctx context.Context, workload *gpucloudv1.GpuWorkload) error {
	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      deploymentName(workload.Name),
			Namespace: workload.Namespace,
		},
	}

	_, err := controllerutil.CreateOrUpdate(ctx, r.Client, deployment, func() error {
		if err := controllerutil.SetControllerReference(workload, deployment, r.Scheme); err != nil {
			return err
		}

		labels := mergeLabels(workload.Spec.Labels, map[string]string{
			managedByLabel: "gpu-cloud-operator",
			workloadLabel:  workload.Name,
		})
		replicas := workloadReplicas(workload)
		image := workload.Spec.Image
		containerPort := workload.Spec.ContainerPort

		deployment.Labels = labels
		deployment.Spec = appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: labels,
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: labels,
				},
				Spec: corev1.PodSpec{
					RuntimeClassName: stringPtrIfNotEmpty(workload.Spec.RuntimeClassName),
					NodeSelector:     workload.Spec.NodeSelector,
					Tolerations:      toCoreTolerations(workload.Spec.Tolerations),
					Containers: []corev1.Container{
						{
							Name:            "workload",
							Image:           image,
							Command:         workload.Spec.Command,
							Args:            workload.Spec.Args,
							ImagePullPolicy: corev1.PullIfNotPresent,
							Resources:       gpuResources(workload.Spec.GpuCount),
						},
					},
				},
			},
		}

		if containerPort > 0 {
			deployment.Spec.Template.Spec.Containers[0].Ports = []corev1.ContainerPort{
				{ContainerPort: containerPort, Protocol: corev1.ProtocolTCP},
			}
		}

		return nil
	})

	return err
}

func (r *GpuWorkloadReconciler) reconcileService(ctx context.Context, workload *gpucloudv1.GpuWorkload) error {
	service := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      serviceName(workload.Name),
			Namespace: workload.Namespace,
		},
	}

	_, err := controllerutil.CreateOrUpdate(ctx, r.Client, service, func() error {
		if err := controllerutil.SetControllerReference(workload, service, r.Scheme); err != nil {
			return err
		}

		labels := mergeLabels(workload.Spec.Labels, map[string]string{
			managedByLabel: "gpu-cloud-operator",
			workloadLabel:  workload.Name,
		})
		servicePort := workload.Spec.ServicePort
		if servicePort == 0 {
			servicePort = 8000
		}
		containerPort := workload.Spec.ContainerPort
		if containerPort == 0 {
			containerPort = 8000
		}

		service.Labels = labels
		spec := corev1.ServiceSpec{
			Type:     corev1.ServiceTypeClusterIP,
			Selector: labels,
			Ports: []corev1.ServicePort{
				{
					Port:       servicePort,
					TargetPort: intstr.FromInt32(containerPort),
					Protocol:   corev1.ProtocolTCP,
				},
			},
		}
		// Preserve fields allocated by the API server on an existing Service;
		// ClusterIP and IP family fields are immutable after creation.
		spec.ClusterIP = service.Spec.ClusterIP
		spec.ClusterIPs = service.Spec.ClusterIPs
		spec.IPFamilies = service.Spec.IPFamilies
		spec.IPFamilyPolicy = service.Spec.IPFamilyPolicy
		service.Spec = spec
		return nil
	})

	return err
}

func (r *GpuWorkloadReconciler) updateStatus(ctx context.Context, workload *gpucloudv1.GpuWorkload) error {
	deployment := &appsv1.Deployment{}
	err := r.Get(ctx, client.ObjectKey{Namespace: workload.Namespace, Name: deploymentName(workload.Name)}, deployment)
	if err != nil && !apierrors.IsNotFound(err) {
		return err
	}

	replicas := workloadReplicas(workload)
	readyReplicas := int32(0)
	availableReplicas := int32(0)
	if err == nil {
		readyReplicas = deployment.Status.ReadyReplicas
		availableReplicas = deployment.Status.AvailableReplicas
	}

	latest := &gpucloudv1.GpuWorkload{}
	if err := r.Get(ctx, client.ObjectKeyFromObject(workload), latest); err != nil {
		return err
	}

	newStatus := gpucloudv1.GpuWorkloadStatus{
		ReadyReplicas:      readyReplicas,
		AvailableReplicas:  availableReplicas,
		ObservedGeneration: latest.Generation,
		DeploymentName:     deploymentName(latest.Name),
		ServiceName:        serviceName(latest.Name),
		Phase:              phaseFor(replicas, readyReplicas, availableReplicas),
		Conditions:         conditionsFor(latest, replicas, availableReplicas),
	}

	if equality.Semantic.DeepEqual(latest.Status, newStatus) {
		return nil
	}

	latest.Status = newStatus
	return r.Status().Update(ctx, latest)
}

// SetupWithManager sets up the controller with the Manager.
func (r *GpuWorkloadReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&gpucloudv1.GpuWorkload{}).
		Owns(&appsv1.Deployment{}).
		Owns(&corev1.Service{}).
		Complete(r)
}

func deploymentName(workloadName string) string {
	return fmt.Sprintf("%s-gpu", workloadName)
}

func serviceName(workloadName string) string {
	return fmt.Sprintf("%s-svc", workloadName)
}

func workloadReplicas(workload *gpucloudv1.GpuWorkload) int32 {
	if workload.Spec.Replicas != nil {
		return *workload.Spec.Replicas
	}
	return 1
}

func mergeLabels(user, managed map[string]string) map[string]string {
	out := make(map[string]string, len(user)+len(managed))
	maps.Copy(out, user)
	maps.Copy(out, managed)
	return out
}

func gpuResources(gpuCount int32) corev1.ResourceRequirements {
	if gpuCount == 0 {
		return corev1.ResourceRequirements{}
	}

	// Both request and limit are set so the scheduler can count the extended
	// resource even when the kubelet/device plugin path expects a limit.
	quantity := resource.MustParse(strconv.Itoa(int(gpuCount)))
	return corev1.ResourceRequirements{
		Requests: corev1.ResourceList{
			"nvidia.com/gpu": quantity,
		},
		Limits: corev1.ResourceList{
			"nvidia.com/gpu": quantity,
		},
	}
}

func stringPtrIfNotEmpty(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}

func toCoreTolerations(in []gpucloudv1.Toleration) []corev1.Toleration {
	if len(in) == 0 {
		return nil
	}
	out := make([]corev1.Toleration, 0, len(in))
	for _, t := range in {
		core := corev1.Toleration{
			Key:      t.Key,
			Operator: corev1.TolerationOperator(t.Operator),
			Value:    t.Value,
			Effect:   corev1.TaintEffect(t.Effect),
		}
		if core.Operator == "" {
			core.Operator = corev1.TolerationOpEqual
		}
		out = append(out, core)
	}
	return out
}

func phaseFor(desired, ready, available int32) string {
	if desired == 0 {
		return ""
	}
	if ready >= desired {
		return "Ready"
	}
	if available > 0 && available < desired {
		return "Degraded"
	}
	return "Pending"
}

func conditionsFor(workload *gpucloudv1.GpuWorkload, desired, available int32) []metav1.Condition {
	now := metav1.Now()

	availableStatus := metav1.ConditionFalse
	availableReason := "NotAvailable"
	availableMessage := fmt.Sprintf("Deployment has %d/%d available replicas", available, desired)
	if available >= desired && desired > 0 {
		availableStatus = metav1.ConditionTrue
		availableReason = "DeploymentAvailable"
		availableMessage = fmt.Sprintf("Deployment has %d/%d available replicas", available, desired)
	}

	return []metav1.Condition{
		{
			Type:               "Available",
			Status:             availableStatus,
			ObservedGeneration: workload.Generation,
			LastTransitionTime: now,
			Reason:             availableReason,
			Message:            availableMessage,
		},
	}
}
