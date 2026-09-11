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

package v1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// GpuWorkloadSpec defines the desired state of a GPU-accelerated cloud workload.
type GpuWorkloadSpec struct {
	// Image is the container image to run, e.g. nvcr.io/nvidia/tritonserver:24.05-py3.
	// +kubebuilder:validation:Required
	Image string `json:"image"`

	// Replicas is the desired number of replicas. Defaults to 1.
	// +kubebuilder:validation:Minimum=0
	// +optional
	Replicas *int32 `json:"replicas,omitempty"`

	// GpuCount is the number of nvidia.com/gpu devices required by each pod.
	// Use 0 for CPU-only workloads or for local Kind demos without a device plugin.
	// +kubebuilder:validation:Minimum=0
	// +kubebuilder:default=0
	// +optional
	GpuCount int32 `json:"gpuCount,omitempty"`

	// RuntimeClassName is an optional RuntimeClass, usually "nvidia" in GPU clusters.
	// +optional
	RuntimeClassName string `json:"runtimeClassName,omitempty"`

	// Command overrides the container command.
	// +optional
	Command []string `json:"command,omitempty"`

	// Args appends container arguments.
	// +optional
	Args []string `json:"args,omitempty"`

	// ServicePort is the port the Service should listen on. Defaults to 8000.
	// +kubebuilder:validation:Minimum=1
	// +kubebuilder:default=8000
	// +optional
	ServicePort int32 `json:"servicePort,omitempty"`

	// ContainerPort is the port exposed by the container. Defaults to 8000.
	// +kubebuilder:validation:Minimum=1
	// +kubebuilder:default=8000
	// +optional
	ContainerPort int32 `json:"containerPort,omitempty"`

	// Labels are merged into pod and deployment labels (metadata labels win).
	// +optional
	Labels map[string]string `json:"labels,omitempty"`

	// NodeSelector constrains pods to nodes with matching labels.
	// +optional
	NodeSelector map[string]string `json:"nodeSelector,omitempty"`

	// Tolerations are copied to the pod template. Useful for GPU node taints.
	// +optional
	Tolerations []Toleration `json:"tolerations,omitempty"`
}

// Toleration is a small subset of corev1.Toleration used to keep the API
// dependency-light while still supporting common GPU node taints.
type Toleration struct {
	// Key is the taint key the toleration applies to.
	Key string `json:"key,omitempty"`
	// Operator represents a key's relationship to the value.
	Operator string `json:"operator,omitempty"`
	// Value is the taint value the toleration matches to.
	Value string `json:"value,omitempty"`
	// Effect indicates the taint effect to match.
	Effect string `json:"effect,omitempty"`
}

// GpuWorkloadStatus defines the observed state of GpuWorkload.
type GpuWorkloadStatus struct {
	// ReadyReplicas is the number of ready pod replicas.
	// +optional
	ReadyReplicas int32 `json:"readyReplicas,omitempty"`

	// AvailableReplicas is the number of available pod replicas reported by Deployment.
	// +optional
	AvailableReplicas int32 `json:"availableReplicas,omitempty"`

	// ObservedGeneration is the generation observed by the controller.
	// +optional
	ObservedGeneration int64 `json:"observedGeneration,omitempty"`

	// DeploymentName is the name of the managed Deployment.
	// +optional
	DeploymentName string `json:"deploymentName,omitempty"`

	// ServiceName is the name of the managed Service.
	// +optional
	ServiceName string `json:"serviceName,omitempty"`

	// Phase is a human-friendly summary: "", "Pending", "Ready", or "Degraded".
	// +optional
	Phase string `json:"phase,omitempty"`

	// Conditions represent the latest observations.
	// +optional
	Conditions []metav1.Condition `json:"conditions,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:path=gpuworkloads,scope=Namespaced,shortName=gw
// +kubebuilder:printcolumn:name="Phase",type=string,JSONPath=`.status.phase`
// +kubebuilder:printcolumn:name="GPUs",type=integer,JSONPath=`.spec.gpuCount`
// +kubebuilder:printcolumn:name="Ready",type=integer,JSONPath=`.status.readyReplicas`
// +kubebuilder:printcolumn:name="Age",type=date,JSONPath=`.metadata.creationTimestamp`

// GpuWorkload is the Schema for a GPU cloud workload.
type GpuWorkload struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   GpuWorkloadSpec   `json:"spec,omitempty"`
	Status GpuWorkloadStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// GpuWorkloadList contains a list of GpuWorkload.
type GpuWorkloadList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []GpuWorkload `json:"items"`
}

func init() {
	SchemeBuilder.Register(&GpuWorkload{}, &GpuWorkloadList{})
}
