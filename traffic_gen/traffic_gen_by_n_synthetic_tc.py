import sys
import random
import math
import heapq
from optparse import OptionParser
import numpy as np
import os
from scipy.stats import genpareto
from scipy.optimize import fsolve
  
def fix_seed(seed):
    np.random.seed(seed)
    random.seed(seed)
class Flow:
	def __init__(self, src, dst, size, t):
		self.src, self.dst, self.size, self.t = src, dst, size, t
	def __str__(self):
		return "%d %d 3 100 %d %.9f"%(self.src, self.dst, self.size, self.t)

def translate_bandwidth(b):
	if b == None:
		return None
	if type(b)!=str:
		return None
	if b[-1] == 'G':
		return float(b[:-1])*1e9
	if b[-1] == 'M':
		return float(b[:-1])*1e6
	if b[-1] == 'K':
		return float(b[:-1])*1e3
	return float(b)

def poisson(lam):
	return -math.log(1-random.random())*lam
def PosNormal(mean, sigma):
	x = np.random.normal(mean,sigma,1)
	return(x if x>=0 else PosNormal(mean,sigma))
if __name__ == "__main__":
	port = 80
	parser = OptionParser()
	parser.add_option("--shard", dest = "shard",type=int, default=0, help="random seed")
	parser.add_option("-f", "--nflows", dest = "nflows", help = "the total number of flows, by default 10000", default = "10000")
	parser.add_option("-n", "--nhost", dest = "nhost", help = "number of hosts")
	parser.add_option("-b", "--bandwidth", dest = "bandwidth", help = "the bandwidth of host link (G/M/K), by default 10G", default = "10G")
	parser.add_option("-o", "--output", dest = "output", help = "the output file", default = "../simulation/mix/")
	options,args = parser.parse_args()

	fix_seed(options.shard)
 
	base_t = 1000000000
	BYTE_TO_BIT=8
	UNIT_G=1000000000
	MTU=1000
	BDP_DICT ={
		3: 10 * MTU,
		5: 10 * MTU,
		7: 10 * MTU,
	} 
	if not options.nhost:
		print "please use -n to enter number of hosts"
		sys.exit(0)
	n_flows = int(options.nflows)
	nhost = int(options.nhost)
	
	bandwidth_base = translate_bandwidth(options.bandwidth)
	if bandwidth_base == None:
		print "bandwidth format incorrect"
		sys.exit(0)
	bandwidth_list_scale=[]
	for link_id in range(nhost-1):
		if link_id==0 or link_id==nhost-2:
			bandwidth_list_scale.append(1)
		else:
			bandwidth_list_scale.append(4)
	
	output_dir = options.output
	if not os.path.exists("%s/stats.npy"%(output_dir)):
		if not os.path.exists(output_dir):
			os.makedirs(output_dir)
		
		# generate flows
		bandwidth_list=[]
		for link_id in range(nhost-1):
			bandwidth_list.append(bandwidth_list_scale[link_id]*bandwidth_base)
		min_size_in_bit=BYTE_TO_BIT * 50  # 50B
		# avg_size_base_in_bit = 4000 *BYTE_TO_BIT # 8000,4000
		BDP = BDP_DICT[nhost]
		avg_size_base_in_bit = BDP//4*BYTE_TO_BIT # 10KB
	
		host_pair_list_ori=[]
		host_pair_to_link_dict={}
		host_pair_to_bandwidth_bottleneck_dict={}
		for i in range(nhost-1):
			for j in range(i+1,nhost):
				src_dst_pair=(i,j)
				if (j-i)!=nhost-1:
					host_pair_list_ori.append(src_dst_pair)
				host_pair_to_link_dict[src_dst_pair]=[]
				for link_id in range(i,j):
					host_pair_to_link_dict[src_dst_pair].append(link_id)
				host_pair_to_bandwidth_bottleneck_dict[src_dst_pair]=np.min([bandwidth_list[link_id] for link_id in host_pair_to_link_dict[src_dst_pair]])
		host_pair_list=[(0,nhost-1)]
		if nhost==2:
			ntc=1
		else:
			ntc=random.randint(2, nhost*(nhost-1)//2)
			host_pair_idx_list=np.random.choice(len(host_pair_list_ori),size=ntc-1,replace=False)
			host_pair_list+=[host_pair_list_ori[i] for i in host_pair_idx_list]
		assert len(host_pair_list)==ntc
		print("lr: ", bandwidth_list, "ntc: ", ntc)
	
		# print("host_pair_list: ", len(host_pair_list), host_pair_list)
		# print("host_pair_to_link_dict: ",len(host_pair_to_link_dict), host_pair_to_link_dict)
		host_list = []
		for i in range(ntc):
			host_list.append((base_t, i))
		heapq.heapify(host_list)
	
		size_distribution_list=["exp","gaussian","lognorm","pareto"]
		size_sigma_range=[5000,50000]
		ia_distribution="lognorm"
		ias_sigma_range=[1.0,2.0]
		load_range=[0.1,0.8]
		load_bottleneck_range=[0.1,0.8]
		
		ntc_in_one=1
		size_dist_candidate=np.random.choice(size_distribution_list,size=ntc_in_one,replace=True)[0]
		size_sigma_candidate=np.random.rand()*(size_sigma_range[1]-size_sigma_range[0])+size_sigma_range[0]
		ias_sigma_candidate=np.random.rand()*(ias_sigma_range[1]-ias_sigma_range[0])+ias_sigma_range[0]
		# ias_sigma_candidate=np.random.choice(ias_sigma_range,size=1,replace=False)[0]
	
		load_candidate=np.random.rand()*(load_range[1]-load_range[0])+load_range[0]
		load_bottleneck_target=np.random.rand()*(load_bottleneck_range[1]-load_bottleneck_range[0])+load_bottleneck_range[0]
  
		load_per_link={}
		for i in range(nhost-1):
			load_per_link[i]=0
		for i in range(ntc):
			load_tmp=load_candidate
			src_dst_pair=host_pair_list[i]
			bandwidth_scale_bottleneck=np.min([bandwidth_list_scale[link_id] for link_id in host_pair_to_link_dict[src_dst_pair]])
			
			for link_id in host_pair_to_link_dict[src_dst_pair]:
				load_per_link[link_id]+=load_tmp*bandwidth_scale_bottleneck/bandwidth_list_scale[link_id]
		tmp=list(load_per_link.values())
		load_bottleneck_cur=np.max(tmp)
		load_bottleneck_link_id=tmp.index(load_bottleneck_cur)
		load_candidate=load_candidate*load_bottleneck_target/load_bottleneck_cur
		print("load_bottleneck: ", load_bottleneck_cur,load_bottleneck_target)
		
		n_flows_tmp=n_flows*ntc+1
		size_distribution=size_dist_candidate
		size_sigma_ori = size_sigma_candidate
		ias_sigma_ori = ias_sigma_candidate
		load = load_candidate
		if size_distribution=="exp":
			mu = avg_size_base_in_bit * (float(size_sigma_ori) / 3000.0)**1.1- min_size_in_bit
			f_sizes_in_byte = ((min_size_in_bit + np.random.exponential(scale=mu, size=(n_flows_tmp,))) / BYTE_TO_BIT).astype("int64") # Byte
		elif size_distribution=="gaussian":
			size_sigma=(float(size_sigma_ori)/4000.0)**1.1
			mu=avg_size_base_in_bit*size_sigma - min_size_in_bit
	
			tmp=np.array([PosNormal(mu, avg_size_base_in_bit*size_sigma) for _ in range(n_flows_tmp)]).squeeze()
			f_sizes_in_byte = (
				(
					min_size_in_bit
					+ tmp
				)
				/ BYTE_TO_BIT  # Byte
			).astype("int64")
		elif size_distribution=="lognorm":
			avg_size_in_bit = avg_size_base_in_bit*(float(size_sigma_ori) / 3000.0)**1.3  # 10KB
			size_sigma=(float(size_sigma_ori)-5000.0) / 45000.0+1.2
			# flow size
			mu = np.log(avg_size_in_bit - min_size_in_bit) - (size_sigma ** 2) / 2
			f_sizes_in_byte = (
				(min_size_in_bit + np.random.lognormal(mean=mu, sigma=size_sigma, size=(n_flows_tmp,)))
				/ BYTE_TO_BIT  # Byte
			).astype("int64")
		elif size_distribution=="pareto":
			avg_size_in_bit=avg_size_base_in_bit*(float(size_sigma_ori)/3000.0)**1.2
			size_sigma=avg_size_in_bit//2.0
			func = lambda x: 5 - np.power(1 + x * (avg_size_in_bit - min_size_in_bit) / size_sigma, 1 / x)
			psi = fsolve(func, 0.5)[0]
			print("psi: ", psi)
			assert psi<1.0
			f_sizes_in_byte = min_size_in_bit + size_sigma * genpareto.rvs(c=psi, size=(n_flows_tmp,))
			f_sizes_in_byte = (f_sizes_in_byte / BYTE_TO_BIT).astype("int64")  # Byte
		else:
			print "size distribution not supported"
			sys.exit(0)
		avg_in_byte = np.mean(f_sizes_in_byte) 
		
		if ia_distribution=="lognorm":
			avg_inter_arrival_in_s = 1/(bandwidth_list[load_bottleneck_link_id]*load/8./avg_in_byte)
			arr_sigma = ias_sigma_ori
			mu = np.log(avg_inter_arrival_in_s) - (arr_sigma**2) / 2
			f_arr_in_ns= (np.random.lognormal(mean=mu, sigma=arr_sigma, size=(n_flows_tmp-1,))* UNIT_G).astype("int64")
	
		# flow_src_dst=[]
		# f_arr_in_ns=[]
		# f_sizes_in_byte=[]
		# ofile.write("%d\n"%n_flows_total)
		data=''
		flow_id_total=0
		t=base_t
		host_pair_list_idx=np.arange(len(host_pair_list))
  
		p_list=np.ones(ntc)
  
		# p_list[0]=np.random.rand()
		# p_list+=0.01

		# p_candidate_list=[ntc, 10, 20, 50, 100]
		# p_candidate=np.random.choice(p_candidate_list,size=1,replace=False)[0]
		# p_list=np.random.rand(ntc)*p_candidate/ntc
		# p_list[0]=1.0
  
		p_list=np.array(p_list)/np.sum(p_list)
		print("ratio: ", p_list[0])
		while (flow_id_total<n_flows_tmp-1):
			host_pair_idx=np.random.choice(host_pair_list_idx,p=p_list)
			# host_pair_idx=np.random.choice(host_pair_list_idx)
			src,dst=host_pair_list[host_pair_idx]
			size=f_sizes_in_byte[flow_id_total]
			data+="%d %d %d 3 100 %d %.9f\n"%(flow_id_total,src, dst, size, t * 1e-9)
			
			# flow_src_dst.append([src,dst])
			# f_arr_in_ns.append(t)
			# f_sizes_in_byte.append(size)
			
			inter_t = f_arr_in_ns[flow_id_total]
			t+=inter_t
			flow_id_total+=1
		n_flows_total=flow_id_total
		t+=UNIT_G
		# ofile.write("%f\n"%((t)/1e9))
		data+="%f"%((t)/1e9)
		data = "{}{}".format("%d\n"%n_flows_total,data)
		# ofile.seek(0)
		ofile = open("%s/flows.txt"%(output_dir), "w")
		ofile.write(data)
		ofile.close()
	
		print("time %f s"%((t)/1e9),"n_flows %d"%(n_flows_total))

		n_flows_done= min(n_flows_total,n_flows_tmp-1)
		end_time=float(np.sum(f_arr_in_ns[: n_flows_done])) / UNIT_G
		utilization = np.sum(f_sizes_in_byte[: n_flows_done])*BYTE_TO_BIT / end_time / bandwidth_list[load_bottleneck_link_id]
		print("utilization: ",np.round(utilization, 3), np.round(load_candidate, 3), size_dist_candidate, size_sigma_candidate, ias_sigma_candidate,end_time)
		stats={
			"n_flows": n_flows_total,
			"ratio": p_list[0],
			"load_bottleneck_target":load_bottleneck_target,
			"host_pair_list":host_pair_list,
			"load_candidate":load_candidate,
			"size_dist_candidate":size_dist_candidate,
			"size_sigma_candidate":size_sigma_candidate,
			"ias_sigma_candidate":ias_sigma_candidate,
		}
		np.save("%s/stats.npy"%(output_dir), stats)  # Byte
		
		# flow_src_dst=np.array(flow_src_dst).astype("int32")
		# f_arr_in_ns=np.array(f_arr_in_ns).astype("int64")
		# f_sizes_in_byte=np.array(f_sizes_in_byte).astype("int64")
		# np.save("%s/flow_sizes.npy"%(output_dir), f_sizes_in_byte)  # Byte
		# np.save("%s/flow_arrival_times.npy"%(output_dir), f_arr_in_ns)  # ns
		# np.save("%s/flow_src_dst.npy"%(output_dir), flow_src_dst) 