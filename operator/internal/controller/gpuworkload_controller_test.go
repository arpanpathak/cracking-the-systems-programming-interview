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
	"testing"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	gpucloudv1 "github.com/arpanpathak/gpu-cloud-operator/api/v1"
)

func testScheme(t *testing.T) *runtime.Scheme {
	t.Helper()
	scheme := runtime.NewScheme()
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(gpucloudv1.AddToScheme(scheme))
	return scheme
}

func TestReconcileCreatesOwnedDeploymentServiceAndStatus(t *testing.T) {
	scheme := testScheme(t)
	replicas := int32(2)

	workload := &gpucloudv1.GpuWorkload{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "triton-demo",
			Namespace: "default",
		},
		Spec: gpucloudv1.GpuWorkloadSpec{
			Image:            "nvcr.io/nvidia/tritonserver:24.05-py3",
			Replicas:         &replicas,
			GpuCount:         1,
			ServicePort:      8000,
			ContainerPort:    8000,
			RuntimeClassName: "nvidia",
		},
	}

	c := fake.NewClientBuilder().
		WithScheme(scheme).
		WithObjects(workload).
		WithStatusSubresource(&gpucloudv1.GpuWorkload{}).
		Build()

	r := &GpuWorkloadReconciler{Client: c, Scheme: scheme}
	ctx := context.Background()

	if _, err := r.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: workload.Name, Namespace: workload.Namespace},
	}); err != nil {
		t.Fatalf("Reconcile() error = %v", err)
	}

	// Deployment was created with the GPU resource and RuntimeClass.
	deployment := &appsv1.Deployment{}
	if err := c.Get(ctx, client.ObjectKey{Namespace: "default", Name: "triton-demo-gpu"}, deployment); err != nil {
		t.Fatalf("expected Deployment: %v", err)
	}
	if deployment.Labels["app.kubernetes.io/managed-by"] != "gpu-cloud-operator" {
		t.Errorf("missing managed-by label: %#v", deployment.Labels)
	}
	if deployment.Spec.Template.Spec.RuntimeClassName == nil || *deployment.Spec.Template.Spec.RuntimeClassName != "nvidia" {
		t.Errorf("expected runtimeClassName nvidia, got %v", deployment.Spec.Template.Spec.RuntimeClassName)
	}
	if len(deployment.OwnerReferences) != 1 {
		t.Errorf("expected one owner reference, got %#v", deployment.OwnerReferences)
	}

	container := deployment.Spec.Template.Spec.Containers[0]
	gpuQuantity, ok := container.Resources.Requests["nvidia.com/gpu"]
	if !ok || gpuQuantity.Cmp(resource.MustParse("1")) != 0 {
		t.Errorf("expected nvidia.com/gpu request=1, got %v", container.Resources.Requests)
	}

	// Service was created and points at the container port.
	service := &corev1.Service{}
	if err := c.Get(ctx, client.ObjectKey{Namespace: "default", Name: "triton-demo-svc"}, service); err != nil {
		t.Fatalf("expected Service: %v", err)
	}
	if len(service.Spec.Ports) != 1 || service.Spec.Ports[0].Port != 8000 {
		t.Errorf("unexpected service ports: %#v", service.Spec.Ports)
	}

	// Status was written (fake Deployment has no ready replicas -> Pending).
	updated := &gpucloudv1.GpuWorkload{}
	if err := c.Get(ctx, client.ObjectKey{Namespace: "default", Name: "triton-demo"}, updated); err != nil {
		t.Fatalf("expected GpuWorkload: %v", err)
	}
	if updated.Status.DeploymentName != "triton-demo-gpu" || updated.Status.ServiceName != "triton-demo-svc" {
		t.Errorf("unexpected status: %#v", updated.Status)
	}
	if updated.Status.Phase != "Pending" {
		t.Errorf("expected phase Pending, got %q", updated.Status.Phase)
	}
}

func TestReconcileCpuWorkloadDoesNotRequestGPU(t *testing.T) {
	scheme := testScheme(t)

	workload := &gpucloudv1.GpuWorkload{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "cpu-demo",
			Namespace: "default",
		},
		Spec: gpucloudv1.GpuWorkloadSpec{
			Image:    "nginx:1.27-alpine",
			GpuCount: 0,
		},
	}

	c := fake.NewClientBuilder().
		WithScheme(scheme).
		WithObjects(workload).
		WithStatusSubresource(&gpucloudv1.GpuWorkload{}).
		Build()

	r := &GpuWorkloadReconciler{Client: c, Scheme: scheme}
	if _, err := r.Reconcile(context.Background(), ctrl.Request{
		NamespacedName: types.NamespacedName{Name: workload.Name, Namespace: workload.Namespace},
	}); err != nil {
		t.Fatalf("Reconcile() error = %v", err)
	}

	deployment := &appsv1.Deployment{}
	if err := c.Get(context.Background(), client.ObjectKey{Namespace: "default", Name: "cpu-demo-gpu"}, deployment); err != nil {
		t.Fatalf("expected Deployment: %v", err)
	}
	container := deployment.Spec.Template.Spec.Containers[0]
	if _, ok := container.Resources.Requests["nvidia.com/gpu"]; ok {
		t.Errorf("CPU workload should not request nvidia.com/gpu: %#v", container.Resources)
	}
}
