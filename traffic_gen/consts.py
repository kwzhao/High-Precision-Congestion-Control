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
size_sigma_range=[5000,50000]
ia_distribution="lognorm"
ias_sigma_range=[1.0,2.0]
load_range=[0.20,0.80]
load_bottleneck_range=[0.20,0.80]
color_list = [
    "cornflowerblue",
    "orange",
    "deeppink",
    "black",
    "blueviolet",
    "seagreen",
]