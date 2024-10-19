import sys
import random
import math
import heapq
from argparse import ArgumentParser
import numpy as np
import os
from scipy.stats import genpareto
from scipy.optimize import fsolve
from collections import defaultdict
from consts import (
    BYTE_TO_BIT,
    UNIT_G,
    size_distribution_list,
    size_sigma_range,
    ia_distribution,
    ias_sigma_range,
    load_range,
    load_bottleneck_range,
    min_size_in_bit,
    avg_size_base_in_bit,
)


def fix_seed(seed):
    np.random.seed(seed)
    random.seed(seed)


def translate_bandwidth(b):
    if b == None:
        return None
    if type(b) != str:
        return None
    if b[-1] == "G":
        return float(b[:-1]) * 1e9
    if b[-1] == "M":
        return float(b[:-1]) * 1e6
    if b[-1] == "K":
        return float(b[:-1]) * 1e3
    return float(b)


def poisson(lam):
    return -math.log(1 - random.random()) * lam


def PosNormal(mean, sigma):
    x = np.random.normal(mean, sigma, 1)
    return x if x >= 0 else PosNormal(mean, sigma)


def export_synthetic_distribution(
    f_sizes_in_byte, output_txt_file, num_percentiles=100
):
    sorted_sizes = np.sort(f_sizes_in_byte)
    percentiles = np.linspace(0, 100, num_percentiles + 1)  # 0% to 100%, inclusive

    # Get the flow size for each percentile
    flow_size_percentiles = np.percentile(sorted_sizes, percentiles)

    # Write the flow sizes and their corresponding percentiles to a text file
    with open(output_txt_file, "w") as f:
        for size, percentile in zip(flow_size_percentiles, percentiles):
            f.write(f"{int(size)} {percentile:.9f}\n")


if __name__ == "__main__":
    parser = ArgumentParser()
    # parser.add_argument(
    #     "--shard", dest="shard", type=int, default=0, help="random seed"
    # )
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        help="the output file",
        default="../simulation/mix/",
    )
    options = parser.parse_args()
    output_dir = options.output
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for shard in range(1000):
        fix_seed(shard)
        size_dist_candidate = np.random.choice(
            size_distribution_list, size=1, replace=True
        )[0]
        size_sigma_candidate = (
            np.random.rand() * (size_sigma_range[1] - size_sigma_range[0])
            + size_sigma_range[0]
        )
        n_flows_tmp = 100000
        if size_dist_candidate == "exp":
            mu = (
                avg_size_base_in_bit * (float(size_sigma_candidate) / 5000.0) ** 2
                - min_size_in_bit
            )
            f_sizes_in_byte = (
                (min_size_in_bit + np.random.exponential(scale=mu, size=(n_flows_tmp,)))
                / BYTE_TO_BIT
            ).astype(
                "int64"
            )  # Byte
        elif size_dist_candidate == "gaussian":
            size_sigma = (float(size_sigma_candidate) / 5000.0) ** 3
            mu = avg_size_base_in_bit * size_sigma - min_size_in_bit

            tmp = np.array(
                [
                    PosNormal(mu, avg_size_base_in_bit * size_sigma)
                    for _ in range(n_flows_tmp)
                ]
            ).squeeze()
            f_sizes_in_byte = ((min_size_in_bit + tmp) / BYTE_TO_BIT).astype(  # Byte
                "int64"
            )
        elif size_dist_candidate == "lognorm":
            avg_size_in_bit = (
                avg_size_base_in_bit * (float(size_sigma_candidate) / 5000.0) ** 2
            )
            # size_sigma = 0.8 + (60000 - float(size_sigma_candidate)) / 30000
            size_sigma = 2.0
            # flow size
            mu = np.log(avg_size_in_bit - min_size_in_bit) - (size_sigma**2) / 2
            f_sizes_in_byte = (
                (
                    min_size_in_bit
                    + np.random.lognormal(
                        mean=mu, sigma=size_sigma, size=(n_flows_tmp,)
                    )
                )
                / BYTE_TO_BIT  # Byte
            ).astype("int64")
        elif size_dist_candidate == "pareto":
            avg_size_in_bit = (
                avg_size_base_in_bit * (float(size_sigma_candidate) / 5000.0) ** 3
            )
            size_sigma = avg_size_in_bit // 2
            func = lambda x: 5 - np.power(
                1 + x * (avg_size_in_bit - min_size_in_bit) / size_sigma, 1 / x
            )
            psi = fsolve(func, 0.5)[0]
            print("psi: ", psi)
            assert psi < 1.0
            f_sizes_in_byte = min_size_in_bit + size_sigma * genpareto.rvs(
                c=psi, size=(n_flows_tmp,)
            )
            f_sizes_in_byte = (f_sizes_in_byte / BYTE_TO_BIT).astype("int64")  # Byte
        else:
            print("size distribution not supported")
            sys.exit(0)
        # Ensure output directory exists

        output_txt_file = os.path.join(output_dir, f"sync-all-{shard}.txt")
        export_synthetic_distribution(
            f_sizes_in_byte, output_txt_file, num_percentiles=100
        )
