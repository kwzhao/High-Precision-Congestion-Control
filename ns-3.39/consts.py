import numpy as np

# extra params, bdp, init_window,buffer_size, enable_pfc
# bfsz=[20,50,10]
# https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=9288775
bfsz=[100,100,10]
# PFC threshold: [15, 45, 65]
# fwin=[10, 30,1000]
fwin=[18, 18, 1000]
# enable_pfc=[0,1]
enable_pfc=[0,0]

CC_DICT = {
    "dctcp": 8,
    "dcqcn_paper_vwin": 1,
    "hp": 3,
    "timely_vwin": 7,
    "powertcp": 2,
    "tcp_bbr": 15,
    "tcp_bic": 16,
    "tcp_cubic": 17,
    "tcp_dctcp": 18,
    "tcp_high_speed": 19,
    "tcp_htcp": 20,
    "tcp_hybla": 21,
    "tcp_illinois": 22,
    "tcp_led_bat": 23,
    "tcp_lp": 24,
    "tcp_scalable": 25,
    "tcp_vegas": 26,
    "tcp_veno": 27,
    "tcp_westwood": 28,
    "tcp_yeah": 29,
    "tcp_linux_reno": 30
}

dctcp_k=[10,60,1]
# dctcp_k=[30,30,1]
dcqcn_k_min=[10, 40,1]
dcqcn_k_max=[50, 100,1]
u_tgt=[70,95,0.01]
# u_tgt=[95,95,0.01]
hpai=[50, 200,10]
# hpai=[25, 25,50]
timely_t_low=[20,80,1000]
timely_t_high=[100,200,1000]

# cc
CC_LIST=list(CC_DICT.keys())

PARAM_NETWORK=[None, bfsz,fwin,enable_pfc]
CC_IDX_BASE=len(PARAM_NETWORK)

PARAM_CC=[None for _ in range(len(CC_LIST))]
CC_PARAM_IDX_BASE=CC_IDX_BASE+len(CC_LIST)

# bdp, init_window,buffer_size, enable_pfc
PARAM_LIST=PARAM_NETWORK + PARAM_CC + [dctcp_k, dcqcn_k_min, dcqcn_k_max, u_tgt, hpai,timely_t_low, timely_t_high] 
 
CONFIG_TO_PARAM_DICT={"bfsz":1, "fwin":2, "pfc":3,"cc":CC_IDX_BASE,"dctcp_k":CC_PARAM_IDX_BASE,"dcqcn_k_min":CC_PARAM_IDX_BASE+1,"dcqcn_k_max":CC_PARAM_IDX_BASE+2,"u_tgt":CC_PARAM_IDX_BASE+3,"hpai":CC_PARAM_IDX_BASE+4,"timely_t_low":CC_PARAM_IDX_BASE+5,"timely_t_high":CC_PARAM_IDX_BASE+6}

DEFAULT_PARAM_VEC=np.zeros(len(PARAM_LIST))

