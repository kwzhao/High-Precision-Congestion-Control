import numpy as np



# extra params, bdp, init_window,buffer_size, enable_pfc
bfsz=[5,100,1]
fwin=[5, 60,1000]
enable_pfc=[0,1]
# cc
CC_IDX_BASE=4
CC_LIST=["dctcp", "timely", "dcqcn", "hp"]

# cc params
CC_PARAM_IDX_BASE=CC_IDX_BASE+len(CC_LIST)
dctcp_k=[1,6,10]
timely_t_low=[1,5,10000]
timely_t_high=[5,25,10000]
dcqcn_k_min=[1, 5,10]
dcqcn_k_max=[5, 25,10]
u_tgt=[0.7,0.95,1]
hpai=[5, 50,100]

# bdp, init_window,buffer_size, enable_pfc
PARAM_LIST=[
    None,
    bfsz,
    fwin,
    enable_pfc,
    None,
    None,
    None,
    None,
    dctcp_k, timely_t_low, timely_t_high, dcqcn_k_min, dcqcn_k_max, u_tgt, hpai   
]
CONFIG_TO_PARAM_DICT={"bfsz":1, "fwin":2, "pfc":3,"cc":CC_IDX_BASE,"dctcp_k":CC_PARAM_IDX_BASE,"timely_t_low":CC_PARAM_IDX_BASE+1,"timely_t_high":CC_PARAM_IDX_BASE+2,"dcqcn_k_min":CC_PARAM_IDX_BASE+3,"dcqcn_k_max":CC_PARAM_IDX_BASE+4,"u_tgt":CC_PARAM_IDX_BASE+5,"hpai":CC_PARAM_IDX_BASE+6}

DEFAULT_PARAM_VEC=np.ones(len(PARAM_LIST))

