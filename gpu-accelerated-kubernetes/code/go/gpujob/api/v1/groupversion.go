// Package v1 defines version v1 of the GpuJob custom resource in the API group
// gpucloud.dev: a request to run one container with a number of GPUs, and the
// status that the controller reports back.
//
// The comments on the types below become the field descriptions in the
// generated CustomResourceDefinition, which kubectl explain prints. The
// +kubebuilder comments are markers that controller-gen reads.
//
// +kubebuilder:object:generate=true
// +groupName=gpucloud.dev
package v1

import (
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/scheme"
)

//go:generate controller-gen object crd paths=. output:crd:dir=../../config/crd

// GroupVersion is the API group and version of the types in this package.
var GroupVersion = schema.GroupVersion{Group: "gpucloud.dev", Version: "v1"}

// SchemeBuilder registers the types in this package with a runtime.Scheme.
var SchemeBuilder = &scheme.Builder{GroupVersion: GroupVersion}

// AddToScheme adds the types in this package to a runtime.Scheme, so that a
// client can encode and decode them.
var AddToScheme = SchemeBuilder.AddToScheme
