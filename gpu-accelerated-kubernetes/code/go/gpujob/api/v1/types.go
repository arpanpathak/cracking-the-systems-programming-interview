package v1

import (
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// GpuJobSpec is a request to run one container with a number of GPUs.
type GpuJobSpec struct {
	// Container image to run.
	Image string `json:"image"`
	// Command to run in the container. When empty, the image's own command runs.
	// +optional
	Command []string `json:"command,omitempty"`
	// Number of GPUs the container requests.
	// +kubebuilder:validation:Minimum=0
	GPUs int32 `json:"gpus"`
}

// Phase is the progress of a job, following the phase of its pod.
// +kubebuilder:validation:Enum=Pending;Running;Succeeded;Failed
type Phase string

// The phases a job moves through.
const (
	// PhasePending means the pod is waiting to be scheduled or for its containers to start.
	PhasePending Phase = "Pending"
	// PhaseRunning means the pod's container is running.
	PhaseRunning Phase = "Running"
	// PhaseSucceeded means the container exited with status 0.
	PhaseSucceeded Phase = "Succeeded"
	// PhaseFailed means the container exited with a non-zero status.
	PhaseFailed Phase = "Failed"
)

// GpuJobStatus is the state of a job as the controller last observed it.
type GpuJobStatus struct {
	// Progress of the job's pod.
	Phase Phase `json:"phase"`
	// The scheduler's reason, when the pod cannot be placed on a node.
	// +optional
	Message string `json:"message,omitempty"`
	// The metadata.generation of the spec that this status describes.
	// +optional
	ObservedGeneration int64 `json:"observedGeneration,omitempty"`
}

// GpuJob runs one container with a number of GPUs.
//
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:shortName=gj
// +kubebuilder:printcolumn:name="GPUs",type=integer,JSONPath=".spec.gpus"
// +kubebuilder:printcolumn:name="Phase",type=string,JSONPath=".status.phase"
type GpuJob struct {
	metav1.TypeMeta `json:",inline"`
	// Standard object metadata: name, namespace, labels, resource version.
	metav1.ObjectMeta `json:"metadata,omitempty"`
	// What the user asks for.
	Spec GpuJobSpec `json:"spec"`
	// What the controller has observed.
	// +optional
	Status GpuJobStatus `json:"status,omitempty"`
}

// GpuJobList is a list of GpuJob objects, as the API server returns it.
//
// +kubebuilder:object:root=true
type GpuJobList struct {
	metav1.TypeMeta `json:",inline"`
	// Standard list metadata, including the list's resource version.
	metav1.ListMeta `json:"metadata,omitempty"`
	// The jobs in the list.
	Items []GpuJob `json:"items"`
}

func init() {
	SchemeBuilder.Register(&GpuJob{}, &GpuJobList{})
}

// StatusFromPod derives a job's status from its pod. generation is the job's
// metadata.generation, recorded as the generation that the status describes.
func StatusFromPod(pod *corev1.Pod, generation int64) GpuJobStatus {
	status := GpuJobStatus{Phase: PhasePending, ObservedGeneration: generation}
	switch pod.Status.Phase {
	case corev1.PodRunning:
		status.Phase = PhaseRunning
	case corev1.PodSucceeded:
		status.Phase = PhaseSucceeded
	case corev1.PodFailed:
		status.Phase = PhaseFailed
	}
	// A pod that cannot be placed explains why in its PodScheduled condition.
	for _, c := range pod.Status.Conditions {
		if c.Type == corev1.PodScheduled && c.Status == corev1.ConditionFalse {
			status.Message = c.Message
		}
	}
	return status
}
