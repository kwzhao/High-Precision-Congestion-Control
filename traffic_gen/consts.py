BYTE_TO_BIT=8
HEADER_SIZE = 48
MTU=1000
BDP_DICT ={
    3: 10 * MTU,
    5: 10 * MTU,
    7: 10 * MTU,
} 
UNIT_K=1000
UNIT_M=1000000
UNIT_G=1000000000

min_size_in_bit=BYTE_TO_BIT * 50  # 50B
avg_size_base_in_bit = MTU*BYTE_TO_BIT # 10KB

size_distribution_list=["exp","gaussian","lognorm","pareto"]
# size_distribution_list=["exp"]
size_sigma_range=[5000,50000]
# size_sigma_range=[30000,30000]
ia_distribution="lognorm"
# ia_distribution="exp"
ias_sigma_range=[1.0,2.0]
# ias_sigma_range=[2.0,2.0]
load_range=[0.20,0.80]
# load_range=[0.95,0.95]
load_bottleneck_range=[0.20,0.80]
# load_bottleneck_range=[0.95,0.95]
color_list = [
    "cornflowerblue",
    "orange",
    "deeppink",
    "black",
    "blueviolet",
    "seagreen",
]