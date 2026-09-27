// gpu_check proves that a container can use the GPU: it prints the device it
// sees, adds two vectors of a million elements on the GPU, and checks the
// result.
//
// How it runs, end to end:
//   1. nvcc compiles this file on the host for the Orin's GPU (-arch=sm_87) and
//      links the CUDA runtime library statically (-cudart static), so the
//      binary needs only the CUDA driver library, libcuda, at run time.
//   2. The binary is copied into the gpu-check:1 image and run in a pod.
//   3. If the pod requested nvidia.com/gpu, the device plugin sets
//      NVIDIA_VISIBLE_DEVICES and the NVIDIA container runtime mounts the GPU's
//      device files and libcuda into the container. If it did not, the
//      container has neither, and the first CUDA call fails.
//   4. The vectors live in managed memory, which the CPU and the GPU can both
//      address, so the program fills them on the CPU, adds them on the GPU,
//      and reads the result on the CPU without explicit copies.
//
// Build: nvcc -O2 -arch=sm_87 -cudart static -o gpu_check gpu_check.cu
#include <cstdio>
#include <cuda_runtime.h>

// kElements is the length of each vector.
constexpr int kElements = 1 << 20;

// kThreads is the number of threads in each block of the add kernel.
constexpr int kThreads = 256;

// add writes a[i] + b[i] to out[i]. Each thread handles one element, and
// threads past the end of the vectors do nothing.
__global__ void add(const float *a, const float *b, float *out, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        out[i] = a[i] + b[i];
    }
}

// main prints the device, runs the addition, and prints the kernel's status
// with the first and last results. It exits with status 1 if no GPU is
// visible, the kernel failed, or the result is wrong.
int main() {
    cudaDeviceProp prop;
    if (cudaGetDeviceProperties(&prop, 0) != cudaSuccess) {
        std::printf("no CUDA device visible\n");
        return 1;
    }
    std::printf("device: %s, compute %d.%d, %d SMs\n", prop.name, prop.major, prop.minor,
                prop.multiProcessorCount);

    float *a, *b, *out;
    cudaMallocManaged(&a, kElements * sizeof(float));
    cudaMallocManaged(&b, kElements * sizeof(float));
    cudaMallocManaged(&out, kElements * sizeof(float));
    for (int i = 0; i < kElements; i++) {
        a[i] = 1.0f;
        b[i] = 2.0f;
    }

    add<<<(kElements + kThreads - 1) / kThreads, kThreads>>>(a, b, out, kElements);
    cudaError_t err = cudaDeviceSynchronize();
    std::printf("kernel: %s, out[0] = %.1f, out[n-1] = %.1f\n", cudaGetErrorString(err),
                out[0], out[kElements - 1]);

    bool ok = err == cudaSuccess && out[kElements - 1] == 3.0f;
    cudaFree(a);
    cudaFree(b);
    cudaFree(out);
    return ok ? 0 : 1;
}
