import os

base_directory = "/data2/lichenni/path_pmn_tc_cc/"
old_suffix = "_k30.txt"
new_suffix = "_k18000.txt"

old_suffix_npy = "_k30.npy"
new_suffix_npy = "_k18000.npy"

try:
    for shard in range(2000):
        for nhosts in [3,5,7]:
        # for nhosts in [3]:
            subdirectory = f"shard{shard}_nflows20000_nhosts{nhosts}_lr10Gbps/"
            directory_to_rename = os.path.join(base_directory, subdirectory)

            for root, _, files in os.walk(directory_to_rename):
                for filename in files:
                    if filename.endswith(old_suffix):
                        old_path = os.path.join(root, filename)
                        new_filename = filename.replace(old_suffix, new_suffix)
                        new_path = os.path.join(root, new_filename)

                        os.rename(old_path, new_path)
                        # print(f"Renamed: {old_path} to {new_path}")
                    if filename.endswith(old_suffix_npy):
                        old_path = os.path.join(root, filename)
                        new_filename = filename.replace(old_suffix_npy, new_suffix_npy)
                        new_path = os.path.join(root, new_filename)

                        os.rename(old_path, new_path)
                        # print(f"Renamed: {old_path} to {new_path}")

            print("All eligible files renamed successfully.")
except FileNotFoundError:
    print(f"Directory not found: {directory_to_rename}")
except Exception as e:
    print(f"An error occurred: {str(e)}")
