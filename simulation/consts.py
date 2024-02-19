import numpy as np

# extra params, bdp, init_window,buffer_size, enable_pfc
bfsz=[10,30,10]
# bfsz=[20,20,10]
# PFC threshold: [15, 45, 65]
fwin=[10, 60,1000]
# fwin=[30, 30, 1000]
enable_pfc=[0,1]
# enable_pfc=[1,1]
# cc
CC_IDX_BASE=4
CC_LIST=["dctcp", "dcqcn_paper_vwin", "hp","timely_vwin"]
# CC_LIST=["dctcp"]

# cc params
CC_PARAM_IDX_BASE=CC_IDX_BASE+4
dctcp_k=[10,60,1]
# dctcp_k=[30,30,1]
dcqcn_k_min=[20, 50,1]
dcqcn_k_max=[50, 100,1]
hpai=[10, 50,50]
# hpai=[25, 25,50]
u_tgt=[70,95,0.01]
# u_tgt=[95,95,0.01]
timely_t_low=[10,50,1000]
timely_t_high=[50,100,1000]

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
    dctcp_k, dcqcn_k_min, dcqcn_k_max, u_tgt, hpai,timely_t_low, timely_t_high,   
]
CONFIG_TO_PARAM_DICT={"bfsz":1, "fwin":2, "pfc":3,"cc":CC_IDX_BASE,"dctcp_k":CC_PARAM_IDX_BASE,"dcqcn_k_min":CC_PARAM_IDX_BASE+1,"dcqcn_k_max":CC_PARAM_IDX_BASE+2,"u_tgt":CC_PARAM_IDX_BASE+3,"hpai":CC_PARAM_IDX_BASE+4,"timely_t_low":CC_PARAM_IDX_BASE+5,"timely_t_high":CC_PARAM_IDX_BASE+6}

DEFAULT_PARAM_VEC=np.zeros(len(PARAM_LIST))

