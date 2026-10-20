#include <cstdlib>
// FEBio linear-solver plugin backed by NVIDIA cuDSS (GPU sparse direct solver).
// Drop-in replacement for "pardiso": same sparse matrix formats (1-based), so FEBio assembly is unchanged.
// Use in a .feb file:  <Control><solver><linear_solver type="cudss"/></solver></Control>
// and load with:       febio4 -import libfebio_cudss.so -i model.feb
// The GPU is cuda:0 of the process (the scheduler sets CUDA_VISIBLE_DEVICES).
#include <FECore/sdk.h>
#include <FECore/LinearSolver.h>
#include <FECore/CompactSymmMatrix.h>
#include <FECore/CompactUnSymmMatrix.h>
#include <FECore/log.h>
#include <cuda_runtime_api.h>
#include <cudss.h>
#include <cstdio>

#define CU(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { fprintf(stderr, "cuDSS plugin: CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return false; } } while (0)
#define DS(x) do { cudssStatus_t s_ = (x); if (s_ != CUDSS_STATUS_SUCCESS) { fprintf(stderr, "cuDSS plugin: cuDSS status %d at %s:%d\n", (int)s_, __FILE__, __LINE__); return false; } } while (0)

class CuDSSSolver : public LinearSolver
{
public:
	CuDSSSolver(FEModel* fem) : LinearSolver(fem) {}
	~CuDSSSolver() { Destroy(); if (m_h) cudssDestroy(m_h); }

	SparseMatrix* CreateSparseMatrix(Matrix_Type ntype) override
	{
		switch (ntype)
		{
		// FEBio stores the lower triangle column-wise == upper triangle row-wise (CSR)
		case REAL_SYMMETRIC     : m_mtype = CUDSS_MTYPE_SYMMETRIC; m_view = CUDSS_MVIEW_UPPER; m_pA = new CompactSymmMatrix(1); break;
		case REAL_UNSYMMETRIC   :
		case REAL_SYMM_STRUCTURE: m_mtype = CUDSS_MTYPE_GENERAL;   m_view = CUDSS_MVIEW_FULL;  m_pA = new CRSSparseMatrix(1); break;
		default: m_pA = nullptr;
		}
		return m_pA;
	}

	bool SetSparseMatrix(SparseMatrix* pA) override
	{
		Destroy();
		m_pA = dynamic_cast<CompactMatrix*>(pA);
		if (dynamic_cast<CompactSymmMatrix*>(pA)) { m_mtype = CUDSS_MTYPE_SYMMETRIC; m_view = CUDSS_MVIEW_UPPER; }
		else { m_mtype = CUDSS_MTYPE_GENERAL; m_view = CUDSS_MVIEW_FULL; }
		return m_pA != nullptr;
	}

	// sparsity pattern is known: upload pattern, create cuDSS objects; analysis is done at the first Factor()
	bool PreProcess() override
	{
		Destroy();
		if (m_h == nullptr) { CU(cudaSetDevice(0)); DS(cudssCreate(&m_h)); }
		m_n = m_pA->Rows(); m_nnz = (int64_t)m_pA->NonZeroes();
		if (m_n == 0) return true;
		CU(cudaMalloc(&d_ptr, sizeof(int) * (m_n + 1)));
		CU(cudaMalloc(&d_ind, sizeof(int) * m_nnz));
		CU(cudaMalloc(&d_val, sizeof(double) * m_nnz));
		CU(cudaMalloc(&d_x, sizeof(double) * m_n));
		CU(cudaMalloc(&d_b, sizeof(double) * m_n));
		CU(cudaMemcpy(d_ptr, m_pA->Pointers(), sizeof(int) * (m_n + 1), cudaMemcpyHostToDevice));
		CU(cudaMemcpy(d_ind, m_pA->Indices(), sizeof(int) * m_nnz, cudaMemcpyHostToDevice));
		cudssIndexBase_t base = (m_pA->Offset() == 1 ? CUDSS_BASE_ONE : CUDSS_BASE_ZERO);
		DS(cudssMatrixCreateCsr(&m_A, m_n, m_n, m_nnz, d_ptr, nullptr, d_ind, d_val, CUDA_R_32I, CUDA_R_64F, m_mtype, m_view, base));
		DS(cudssMatrixCreateDn(&m_X, m_n, 1, m_n, d_x, CUDA_R_64F, CUDSS_LAYOUT_COL_MAJOR));
		DS(cudssMatrixCreateDn(&m_B, m_n, 1, m_n, d_b, CUDA_R_64F, CUDSS_LAYOUT_COL_MAJOR));
		DS(cudssConfigCreate(&m_cfg));
		DS(cudssDataCreate(m_h, &m_data));
		int ir = m_irSteps;
		DS(cudssConfigSet(m_cfg, CUDSS_CONFIG_IR_N_STEPS, &ir, sizeof(ir)));
		// optional hybrid memory mode (factors partly in host RAM) for models whose factors exceed GPU memory
		// (enable with FEBIO_CUDSS_HYBRID=1; added 2026-10-20 for the 1.5 M-equation 0.1 mm cage mesh-convergence case)
		const char* hy = getenv("FEBIO_CUDSS_HYBRID");
		if (hy && atoi(hy) == 1) { int on = 1; DS(cudssConfigSet(m_cfg, CUDSS_CONFIG_HYBRID_MODE, &on, sizeof(on))); fprintf(stderr, "cuDSS plugin: hybrid memory mode on\n"); }
		m_analyzed = false;
		return LinearSolver::PreProcess();
	}

	bool Factor() override
	{
		if (m_n == 0) return true;
		CU(cudaMemcpy(d_val, m_pA->Values(), sizeof(double) * m_nnz, cudaMemcpyHostToDevice));
		if (!m_analyzed)
		{
			DS(cudssExecute(m_h, CUDSS_PHASE_ANALYSIS, m_cfg, m_data, m_A, m_X, m_B));
			m_analyzed = true;
		}
		DS(cudssExecute(m_h, CUDSS_PHASE_FACTORIZATION, m_cfg, m_data, m_A, m_X, m_B));
		CU(cudaDeviceSynchronize());
		int info = 0; size_t sz = 0;
		DS(cudssDataGet(m_h, m_data, CUDSS_DATA_INFO, &info, sizeof(info), &sz));
		if (info != 0) { feLogError("cuDSS factorization info = %d (singular / zero pivot)", info); return false; }
		return true;
	}

	bool BackSolve(double* x, double* b) override
	{
		if (m_n == 0) return true;
		CU(cudaMemcpy(d_b, b, sizeof(double) * m_n, cudaMemcpyHostToDevice));
		DS(cudssExecute(m_h, CUDSS_PHASE_SOLVE, m_cfg, m_data, m_A, m_X, m_B));
		CU(cudaMemcpy(x, d_x, sizeof(double) * m_n, cudaMemcpyDeviceToHost));
		UpdateStats(1);
		return true;
	}

	void Destroy() override
	{
		if (m_A) cudssMatrixDestroy(m_A);
		if (m_X) cudssMatrixDestroy(m_X);
		if (m_B) cudssMatrixDestroy(m_B);
		if (m_data) cudssDataDestroy(m_h, m_data);
		if (m_cfg) cudssConfigDestroy(m_cfg);
		m_A = m_X = m_B = nullptr; m_data = nullptr; m_cfg = nullptr;
		for (void** p : {(void**)&d_ptr, (void**)&d_ind, (void**)&d_val, (void**)&d_x, (void**)&d_b})
			if (*p) { cudaFree(*p); *p = nullptr; }
		m_analyzed = false;
	}

private:
	CompactMatrix* m_pA = nullptr;
	cudssMatrixType_t m_mtype = CUDSS_MTYPE_SYMMETRIC;
	cudssMatrixViewType_t m_view = CUDSS_MVIEW_UPPER;
	int m_n = 0; int64_t m_nnz = 0;
	int m_irSteps = 1;   // iterative refinement steps (Pardiso in FEBio uses 1)
	bool m_analyzed = false;
	cudssHandle_t m_h = nullptr; cudssConfig_t m_cfg = nullptr; cudssData_t m_data = nullptr;
	cudssMatrix_t m_A = nullptr, m_X = nullptr, m_B = nullptr;
	int* d_ptr = nullptr; int* d_ind = nullptr; double* d_val = nullptr; double* d_x = nullptr; double* d_b = nullptr;

	DECLARE_FECORE_CLASS();
};

BEGIN_FECORE_CLASS(CuDSSSolver, LinearSolver)
	ADD_PARAMETER(m_irSteps, "ir_steps");
END_FECORE_CLASS();

FECORE_PLUGIN int GetSDKVersion() { return FE_SDK_VERSION; }

FECORE_PLUGIN void PluginInitialize(FECoreKernel& febio)
{
	FECoreKernel::SetInstance(&febio);
	REGISTER_FECORE_CLASS(CuDSSSolver, "cudss");
}
