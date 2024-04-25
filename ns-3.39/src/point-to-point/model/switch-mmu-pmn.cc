#include <iostream>
#include <fstream>
#include "ns3/packet.h"
#include "ns3/simulator.h"
#include "ns3/object-vector.h"
#include "ns3/uinteger.h"
#include "ns3/log.h"
#include "ns3/assert.h"
#include "ns3/global-value.h"
#include "ns3/boolean.h"
#include "ns3/simulator.h"
#include "ns3/random-variable.h"
#include "switch-mmu-pmn.h"

NS_LOG_COMPONENT_DEFINE("SwitchMmuPmn");
namespace ns3 {
	TypeId SwitchMmuPmn::GetTypeId(void){
		static TypeId tid = TypeId("ns3::SwitchMmuPmn")
			.SetParent<Object>()
			.AddConstructor<SwitchMmuPmn>();
		return tid;
	}

	SwitchMmuPmn::SwitchMmuPmn(void){
		buffer_size = 12 * 1024 * 1024;
		reserve = 4 * 1024;
		resume_offset = 3 * 1024;

		// headroom
		shared_used_bytes = 0;
		memset(hdrm_bytes, 0, sizeof(hdrm_bytes));
		memset(ingress_bytes, 0, sizeof(ingress_bytes));
		memset(paused, 0, sizeof(paused));
		memset(egress_bytes, 0, sizeof(egress_bytes));
	}
	bool SwitchMmuPmn::CheckIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		if (psize + hdrm_bytes[port][qIndex] > headroom[port] && psize + GetSharedUsed(port, qIndex) > GetPfcThreshold(port)){
			printf("%lu %u Drop: queue:%u,%u: Headroom full\n", Simulator::Now().GetTimeStep(), node_id, port, qIndex);
			// for (uint32_t i = 1; i < 64; i++)
			// 	printf("(%u,%u)", hdrm_bytes[i][3], ingress_bytes[i][3]);
			// printf("\n");
			return false;
		}
		return true;
	}
	bool SwitchMmuPmn::CheckEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		return true;
	}
	void SwitchMmuPmn::UpdateIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		uint32_t new_bytes = ingress_bytes[port][qIndex] + psize;
		if (new_bytes <= reserve){
			ingress_bytes[port][qIndex] += psize;
		}else {
			uint32_t thresh = GetPfcThreshold(port);
			if (new_bytes - reserve > thresh){
				hdrm_bytes[port][qIndex] += psize;
			}else {
				ingress_bytes[port][qIndex] += psize;
				shared_used_bytes += std::min(psize, new_bytes - reserve);
			}
		}
	}
	void SwitchMmuPmn::UpdateEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		egress_bytes[port][qIndex] += psize;
	}
	void SwitchMmuPmn::RemoveFromIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		uint32_t from_hdrm = std::min(hdrm_bytes[port][qIndex], psize);
		uint32_t from_shared = std::min(psize - from_hdrm, ingress_bytes[port][qIndex] > reserve ? ingress_bytes[port][qIndex] - reserve : 0);
		hdrm_bytes[port][qIndex] -= from_hdrm;
		ingress_bytes[port][qIndex] -= psize - from_hdrm;
		shared_used_bytes -= from_shared;
	}
	void SwitchMmuPmn::RemoveFromEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize){
		egress_bytes[port][qIndex] -= psize;
	}
	bool SwitchMmuPmn::CheckShouldPause(uint32_t port, uint32_t qIndex){
		return !paused[port][qIndex] && (hdrm_bytes[port][qIndex] > 0 || GetSharedUsed(port, qIndex) >= GetPfcThreshold(port));
	}
	bool SwitchMmuPmn::CheckShouldResume(uint32_t port, uint32_t qIndex){
		if (!paused[port][qIndex])
			return false;
		uint32_t shared_used = GetSharedUsed(port, qIndex);
		return hdrm_bytes[port][qIndex] == 0 && (shared_used == 0 || shared_used + resume_offset <= GetPfcThreshold(port));
	}
	void SwitchMmuPmn::SetPause(uint32_t port, uint32_t qIndex){
		paused[port][qIndex] = true;
	}
	void SwitchMmuPmn::SetResume(uint32_t port, uint32_t qIndex){
		paused[port][qIndex] = false;
	}
	//TODO by cl
	uint32_t SwitchMmuPmn::GetPfcThreshold(uint32_t port){
		uint32_t res=(buffer_size - total_hdrm - total_rsrv - shared_used_bytes) >> pfc_a_shift[port];
		// printf("PFC threshold: %u, buffer_size:%u, total_hdrm:%u, total_rsrv:%u,reserve:%u, shared_used_bytes:%u, pfc_a_shift[port]:%u \n", res, buffer_size, total_hdrm, total_rsrv,reserve, shared_used_bytes, pfc_a_shift[port]);
		return res;
	}
	uint32_t SwitchMmuPmn::GetSharedUsed(uint32_t port, uint32_t qIndex){
		uint32_t used = ingress_bytes[port][qIndex];
		return used > reserve ? used - reserve : 0;
	}
	bool SwitchMmuPmn::ShouldSendCN(uint32_t ifindex, uint32_t qIndex){
		// printf("ShouldSendCN: %u, %u, %u, %u, %u\n", ifindex, qIndex,egress_bytes[ifindex][qIndex], kmax[ifindex], kmin[ifindex]);
		if (qIndex == 0)
			return false;
		if (egress_bytes[ifindex][qIndex] > kmax[ifindex])
			return true;
		if (egress_bytes[ifindex][qIndex] > kmin[ifindex]){
			double p = pmax[ifindex] * double(egress_bytes[ifindex][qIndex] - kmin[ifindex]) / (kmax[ifindex] - kmin[ifindex]);
			if (UniformVariable(0, 1).GetValue() < p)
				return true;
		}
		return false;
	}
	void SwitchMmuPmn::ConfigEcn(uint32_t port, uint32_t _kmin, uint32_t _kmax, double _pmax){
		kmin[port] = _kmin * 1000;
		kmax[port] = _kmax * 1000;
		pmax[port] = _pmax;
		// printf("ECN: %u, %u, %u, %f\n",port, kmin[port], kmax[port], pmax[port]);
	}
	void SwitchMmuPmn::ConfigHdrm(uint32_t port, uint32_t size){
		headroom[port] = size;
	}
	void SwitchMmuPmn::ConfigNPort(uint32_t n_port){
		total_hdrm = 0;
		total_rsrv = 0;
		for (uint32_t i = 1; i <= n_port; i++){
			total_hdrm += headroom[i];
			total_rsrv += reserve;
		}
	}
	void SwitchMmuPmn::ConfigBufferSize(uint32_t size){
		buffer_size = size;
	}
	void SwitchMmuPmn::ConfigReserve(uint32_t size){
		reserve = size;
	}
}
