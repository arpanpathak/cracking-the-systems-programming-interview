// gpu_info prints what one Kubernetes nvidia.com/gpu unit contains on the
// machine it runs on: the GPU's compute units, memory, caches, and engines.
//
// How it runs, end to end:
//   1. nvcc compiles this file on the host for the Orin's GPU (-arch=sm_87) and
//      links the CUDA runtime library statically (-cudart static), so the
//      binary needs only the CUDA driver library, libcuda, at run time.
//   2. The binary is copied into the gpu-sharing:1 image and run in a pod that
//      requests nvidia.com/gpu: 1.
//   3. The device plugin's Allocate answer sets NVIDIA_VISIBLE_DEVICES in the
//      container, and the NVIDIA container runtime mounts the GPU's device
//      files and libcuda into it.
//   4. The CUDA runtime calls below load libcuda, which opens the device files
//      and asks the kernel driver for the device's properties.
//
// Build: nvcc -O2 -arch=sm_87 -cudart static -o gpu_info gpu_info.cu
#include <cstdio>
#include <cuda_runtime.h>

// kGiB is the number of bytes in one gibibyte, for printing memory sizes.
constexpr double kGiB = 1024.0 * 1024.0 * 1024.0;

// main queries device 0 and prints one property per line. It exits with
// status 1 when no CUDA device is visible, for example in a container that
// was not given a GPU.
int main() {
    cudaDeviceProp p;
    if (cudaGetDeviceProperties(&p, 0) != cudaSuccess) {
        std::printf("no CUDA device visible\n");
        return 1;
    }

    // cudaMemGetInfo reports the memory that the driver can still allocate and
    // the total. On an integrated GPU both come from the system's shared RAM.
    size_t free_bytes = 0, total_bytes = 0;
    cudaMemGetInfo(&free_bytes, &total_bytes);

    std::printf("device                      %s\n", p.name);
    std::printf("compute capability          %d.%d\n", p.major, p.minor);
    std::printf("integrated with the CPU     %s\n", p.integrated ? "yes" : "no");
    std::printf("streaming multiprocessors   %d\n", p.multiProcessorCount);
    std::printf("max resident threads/SM     %d\n", p.maxThreadsPerMultiProcessor);
    std::printf("registers per SM            %d\n", p.regsPerMultiprocessor);
    std::printf("shared memory per SM        %zu KiB\n", p.sharedMemPerMultiprocessor / 1024);
    std::printf("L2 cache                    %d KiB\n", p.l2CacheSize / 1024);
    std::printf("device memory (total)       %.1f GiB\n", total_bytes / kGiB);
    std::printf("device memory (free now)    %.1f GiB\n", free_bytes / kGiB);
    std::printf("copy engines                %d\n", p.asyncEngineCount);
    std::printf("concurrent kernels          %s\n", p.concurrentKernels ? "yes" : "no");
    std::printf("managed memory              %s\n", p.managedMemory ? "yes" : "no");
    return 0;
}
