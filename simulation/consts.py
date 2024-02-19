import numpy as np

# extra params, bdp, init_window,buffer_size, enable_pfc
# bfsz=[100,300,1]
bfsz=[200,200,1]
# PFC threshold: [23, 62]
# fwin=[10, 60,1000]
fwin=[30, 30, 1000]
enable_pfc=[1,1]
# cc
CC_IDX_BASE=4
# CC_LIST=["dctcp", "timely_vwin", "dcqcn_paper_vwin", "hp"]
CC_LIST=["hp"]

# cc params
CC_PARAM_IDX_BASE=CC_IDX_BASE+4
# dctcp_k=[10,60,1]
dctcp_k=[30,30,1]
timely_t_low=[5,20,1000]
timely_t_high=[20,50,1000]
dcqcn_k_min=[10, 40,1]
dcqcn_k_max=[40, 100,1]
# u_tgt=[70,95,0.01]
u_tgt=[95,95,0.01]
hpai=[10, 50,50]
# hpai=[50, 50,50]

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

DEFAULT_PARAM_VEC=np.zeros(len(PARAM_LIST))

