// gpu_load keeps the GPU busy with a fixed amount of arithmetic and prints how
// long the work took. Running it alone and running several copies that share
// one GPU shows how much GPU time each copy receives.
//
// How it runs, end to end:
//   1. nvcc compiles this file on the host (-arch=sm_87, -cudart static), and
//      the binary is copied into the gpu-sharing:1 image.
//   2. Each pod of the gpu-load Job runs it with the pod's name as argument and
//      receives one nvidia.com/gpu unit, so the NVIDIA container runtime gives
//      it the GPU's device files and libcuda.
//   3. main launches the spin kernel kRounds times on the default stream. The
//      launches queue up on the GPU, and cudaDeviceSynchronize waits until all
//      of them have finished, so the measured time covers the GPU work.
//   4. When several pods share the GPU through time-slicing, the driver
//      switches between their CUDA contexts, and each copy's time grows by the
//      share of the GPU that the others take.
//
// Build: nvcc -O2 -arch=sm_87 -cudart static -o gpu_load gpu_load.cu
#include <chrono>
#include <cstdio>
#include <cuda_runtime.h>

// kBlocks and kThreads give 262,144 threads per launch, enough to occupy every
// SM of the GPU many times over.
constexpr int kBlocks = 1024;
constexpr int kThreads = 256;

// kIterations is the number of multiply-adds each thread performs per launch.
constexpr int kIterations = 200000;

// kRounds is the number of kernel launches in one measurement.
constexpr int kRounds = 10;

// spin performs `iterations` dependent multiply-adds on a per-thread value and
// stores the result, so the compiler cannot remove the loop.
__global__ void spin(float *out, int iterations) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    float x = i * 1e-6f;
    for (int k = 0; k < iterations; k++) {
        x = x * 1.000001f + 0.5f;
    }
    out[i] = x;
}

// main runs the measurement and prints "<name>: <result>, <milliseconds> ms",
// where name is the first argument. It exits with status 1 if the GPU reported
// an error.
int main(int argc, char **argv) {
    const char *name = argc > 1 ? argv[1] : "load";
    float *out;
    cudaMalloc(&out, kBlocks * kThreads * sizeof(float));

    auto start = std::chrono::steady_clock::now();
    for (int r = 0; r < kRounds; r++) {
        spin<<<kBlocks, kThreads>>>(out, kIterations);
    }
    cudaError_t err = cudaDeviceSynchronize();
    double ms = std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - start).count();

    std::printf("%s: %s, %.0f ms\n", name, cudaGetErrorString(err), ms);
    cudaFree(out);
    return err == cudaSuccess ? 0 : 1;
}
