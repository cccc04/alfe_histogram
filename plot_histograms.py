import json
import os
import re
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timezone, timedelta

# Fixed number of bins (e.g., 20 bins)
N_BINS = 20

def read_json_files(file_paths, impedance):
    # Define per-channel parameters (excluding uniformity)
    channel_params = [
        "baseline", "noise_rms_mv", "gain", "eni", 
        "peaking_time", "max_non_linearity", "fit_gain", 
        "gain_crude", "i2c_margin_list"
    ]
    
    # List of channels found in the JSON files
    channels = [
        "CH0 HG", "CH1 HG", "CH2 HG", "CH3 HG", 
        "CH0 LG", "CH1 LG", "CH2 LG", "CH3 LG", 
        "SUM x3", "SUM x1", "LG0", "LG1", "LG2", "LG3", 
        "HG0", "HG1", "HG2", "HG3", "400_kHz", "1_MHz"
    ]
    
    # Initialize per-channel data storage
    channel_values = {channel: {param: [] for param in channel_params} for channel in channels}
    power_ldo_values = {}
    gain_ratio_values = {0: [], 1: [], 2: [], 3: []}
    uniformity_hg = {"gain_uniformity": [], "peaking_time_uniformity": [], "baseline_uniformity": []}
    uniformity_lg = {"gain_uniformity": [], "peaking_time_uniformity": [], "baseline_uniformity": []}
    s_n = []

    def process_results(data, key_suffix, params):
        if key_suffix in data:
            results = data[key_suffix]
            channel_list = results.get("channel_list", results.get("i2c_frequency_list", None))
            if not channel_list:
                print(f"Warning: Neither 'channel_list' nor 'i2c_frequency_list' found in {key_suffix}")
                return
            for idx, channel in enumerate(channel_list):
                for param in params:
                    if param in results:
                        value = results[param]
                        val = value[idx] if isinstance(value, list) else value
                        if channel in channel_values and param in channel_values[channel]:
                            channel_values[channel][param].append(val)
           
    vecs = []
    vece = []
    def populate(vec, month, day, hour, minute, second):
        vec.append(datetime(2025, month, day, hour, minute, second, tzinfo=timezone(timedelta(hours=-4))))

    populate(vecs, 3, 28, 15, 43, 0)   # 3:43 PM = 15:43
    populate(vece, 3, 28, 20, 48, 59)  # 8:48 PM = 20:48

    # 3/31
    populate(vecs, 3, 31, 11, 24, 0)   # 11:24 AM = 11:24
    populate(vece, 3, 31, 22, 45, 59)  # 10:45 PM = 22:45

    # 4/1
    populate(vecs, 4, 1, 16, 26, 0)    # 4:26 PM = 16:26
    populate(vece, 4, 2, 1, 42, 59)    # 1:42 AM next day = 4/2 01:42

    # 4/2 - first interval
    populate(vecs, 4, 2, 9, 25, 0)     # 9:25 AM = 09:25
    populate(vece, 4, 2, 14, 2, 59)    # 2:02 PM = 14:02

    # 4/2 - second interval
    populate(vecs, 4, 2, 19, 18, 0)    # 4:56 PM = 16:56
    populate(vece, 4, 3, 10, 58, 59)   # 10:58 AM next day = 4/3 10:58

    # 4/3
    populate(vecs, 4, 3, 15, 15, 0)    # 3:15 PM = 15:15
    populate(vece, 4, 3, 23, 3, 59)    # 11:03 PM = 23:03

    # 4/4
    populate(vecs, 4, 4, 11, 58, 0)    # 11:58 AM = 11:58
    populate(vece, 4, 5, 11, 36, 59)   # 11:36 AM same day

    # 4/7
    populate(vecs, 4, 7, 16, 4, 0)     # 4:04 PM = 16:04
    populate(vece, 4, 7, 23, 45, 59)   # 11:45 PM = 23:45

    # 4/9
    populate(vecs, 4, 9, 17, 37, 0)    # 5:37 PM = 17:37
    populate(vece, 4, 10, 3, 48, 59)   # 3:48 AM next day = 4/10 03:48

    # 4/10
    populate(vecs, 4, 10, 17, 3, 0)    # 5:03 PM = 17:03
    populate(vece, 4, 10, 18, 14, 59)  # 6:14 PM = 18:14

    # 4/24
    populate(vecs, 4, 24, 17, 18, 0)   # 5:18 PM = 17:18
    populate(vece, 4, 25, 2, 35, 59)   # 2:35 AM next day = 4/25 02:35

    # 4/25
    populate(vecs, 4, 25, 16, 33, 0)   # 4:33 PM = 16:33
    populate(vece, 4, 25, 20, 33, 59)  # 8:33 PM = 20:33

    # 4/28
    populate(vecs, 4, 28, 16, 8, 0)    # 4:08 PM = 16:08
    populate(vece, 4, 28, 20, 11, 59)  # 8:11 PM = 20:11

    # 5/2
    populate(vecs, 5, 2, 15, 44, 0)    # 3:44 PM = 15:44
    populate(vece, 5, 2, 20, 18, 59)   # 8:18 PM = 20:18

    for file_path in file_paths:
        with open(file_path, 'r') as f:
            data = json.load(f)

        stamp = int(re.search(r'(\d{10})', file_path).group(1))
        dt = datetime.fromtimestamp(stamp, tz=timezone(timedelta(hours=-4)))  # or use fromtimestamp() for local time


        out = True
        for i in range(len(vecs)):
            if vecs[i] <= dt <= vece[i]:
                out = False
                '''
                # Get the parent folder of the file
                parent_folder = os.path.dirname(file_path)

                # Set destination folder based on the index
                dest_folder = f"folder_{i}"
                os.makedirs(dest_folder, exist_ok=True)

                # Get the base name of the parent folder (e.g., "data1" from "/path/to/data1/file.txt")
                folder_name = os.path.basename(parent_folder)

                # Set the final destination path for the copied folder
                dest_path = os.path.join(dest_folder, folder_name)

                # Copy the entire parent folder to the destination
                shutil.copytree(parent_folder, dest_path, dirs_exist_ok=True)
                '''
                break  # Stop checking once we've found the correct range

        match = re.search(r'(\d{3}-\s\d{5})', file_path)
        if not match:
            match = re.search(r'(\d{3}-\d{5})', file_path)  # Handle cases with space

        if out:
            continue
        
        if match:
            if match.group(1) not in s_n:
                s_n.append(match.group(1))
            else:
                continue
        else:
            print(f"Warning({file_path}): No match found")
            continue

        # Process HG
        key_hg = f"results_noise_{impedance}_all_ch_HG"
        process_results(data, key_hg, ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
        if key_hg in data:
            results = data[key_hg]
            for key in uniformity_hg:
                uniformity_hg[key].append(results.get(key))

        # Process LG
        key_lg = f"results_noise_{impedance}_all_ch_LG"
        process_results(data, key_lg, ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
        if key_lg in data:
            results = data[key_lg]
            for key in uniformity_lg:
                uniformity_lg[key].append(results.get(key))

        # Process sum and linearity data
        process_results(data, f"results_noise_{impedance}_sum_x3", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
        process_results(data, f"results_noise_{impedance}_sum_x1", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
        process_results(data, f"results_linearity_{impedance}_sum_x3", ["max_non_linearity", "fit_gain"])
        process_results(data, f"results_linearity_{impedance}_sum_x1", ["max_non_linearity", "fit_gain"])
        process_results(data, f"results_linearity_{impedance}_all_ch_HG", ["max_non_linearity", "fit_gain"])
        process_results(data, f"results_linearity_{impedance}_all_ch_LG", ["max_non_linearity", "fit_gain"])
        process_results(data, f"results_channel_enable_{impedance}", ["gain_crude"])
        process_results(data, "i2c_results", ["i2c_margin_list"])

        # Gain ratio
        gain_ratio_key = f"gain_ratio_{impedance}"
        if gain_ratio_key in data:
            results = data[gain_ratio_key]
            if isinstance(results, list):
                for idx, value in enumerate(results):
                    if idx in gain_ratio_values:
                        gain_ratio_values[idx].append(value)
            else:
                print(f"Warning: Expected a list for {gain_ratio_key}, but found {type(results)}")

        # Power LDO
        if "power_ldo" in data:
            for ldo in data["power_ldo"]:
                ldo_name = ldo.get("name")
                if not ldo_name:
                    continue
                if ldo_name not in power_ldo_values:
                    power_ldo_values[ldo_name] = {}
                for key, value in ldo.items():
                    if key == "name":
                        continue
                    if key not in power_ldo_values[ldo_name]:
                        power_ldo_values[ldo_name][key] = []
                    power_ldo_values[ldo_name][key].append(value)

    return channel_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values

def load_bin_widths(output_directory, filename="bin_widths.json"):
    """
    Load the bin widths from a JSON file.
    """
    file_path = os.path.join(output_directory, filename)
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            bin_widths = json.load(f)
        print(f"Loaded bin widths from {file_path}")
        return bin_widths
    else:
        print(f"No bin widths file found at {file_path}")
        return None

def load_existing_xlim(output_directory, impedance):
    xlim_file_path = os.path.join(output_directory, f"limits.json")
    if os.path.exists(xlim_file_path):
        with open(xlim_file_path, "r") as f:
            return json.load(f)  # Load existing xlim limits
    return {}  # Return an empty dictionary if no existing file is found

def plot_histograms(data_dict, output_directory, root_directory, impedance, label, key_prefix, histogram_type, xlimb):
    if xlimb:
        xlim_limits = load_existing_xlim(root_directory, impedance)

    for outer_key, inner_dict in data_dict.items():
        if not isinstance(inner_dict, dict):
            inner_dict = {outer_key: inner_dict}
            outer_key = None

        for param, values in inner_dict.items():
            if values:
                plt.figure(figsize=(10, 6))
                full_key = f"{key_prefix}_{param}_{impedance}" if outer_key is None else f"{outer_key}_{param}_{impedance}"

                # Default bin width
                bw = None

                # If no custom bin width and xlimb is enabled, compute it from xlim
                if xlimb and full_key in xlim_limits:
                    xlim = xlim_limits[full_key]
                    bw = (xlim["max"] - xlim["min"]) / N_BINS

                # Compute bins
                bins = np.arange(min(values), max(values) + bw, bw) if bw else N_BINS
                plt.hist(values, bins=bins, alpha=0.7)

                # Draw x-limits and markers if xlim enabled
                if xlimb and full_key in xlim_limits:
                    xlim = xlim_limits[full_key]
                    plt.xlim(xlim["min"] - 0.125 * (xlim["max"] - xlim["min"]),
                             xlim["max"] + 0.125 * (xlim["max"] - xlim["min"]))
    
                    # Add vertical lines with formatted labels
                    plt.axvline(x=xlim["min"], color='red', linestyle='--', label=f'min: {xlim["min"]:.2f}')
                    plt.axvline(x=xlim["max"], color='red', linestyle='--', label=f'max: {xlim["max"]:.2f}')
    
                    plt.legend(loc='upper right', fontsize=14)
                elif xlimb:
                    print(f"xlim for {full_key} does not exist in file")

                title_key = f"{label} {param}" if outer_key is None else f"{param} for {outer_key}"
                plt.title(f"{title_key} - {impedance}")
                plt.xlabel(param)
                plt.ylabel("Count")
                plt.grid(True)
                plt.tight_layout()

                filename = f"{label.lower()}_{param}_{impedance}_histogram.png" if outer_key is None \
                    else f"{outer_key}_{param}_{impedance}_histogram.png"
                plt.savefig(os.path.join(output_directory, filename), dpi=300)
                plt.close()



def main(root_directory, output_directory, xlimb = False):
    impedance = ["25", "50"]
    current_directory = "./"
    for impedance_index in impedance:
        os.makedirs(output_directory, exist_ok=True)
   
        # Collect all results_all.json file paths.
        file_paths = []
        for dirpath, _, filenames in os.walk(root_directory):
            if "results_all.json" in filenames:
                file_paths.append(os.path.join(dirpath, "results_all.json"))
   
        channel_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values = read_json_files(file_paths, impedance_index)
   
        plot_histograms(channel_values, output_directory, current_directory, impedance_index, "Channel", "channel", "channel_histograms", xlimb)
        plot_histograms(power_ldo_values, output_directory, current_directory, impedance_index, "Power_LDO", "power_ldo", "power_ldo_histograms", xlimb)
        plot_histograms(uniformity_hg, output_directory, current_directory, impedance_index, "HG", "hg", "uniformity_histograms", xlimb)
        plot_histograms(uniformity_lg, output_directory, current_directory, impedance_index, "LG", "lg", "uniformity_histograms", xlimb)
        plot_histograms(gain_ratio_values, output_directory, current_directory, impedance_index, "Gain_Ratio", "gain_ratio", "gain_ratio_histograms", xlimb)

if __name__ == '__main__':
    root_directory = "../all/"  # Update with your actual root directory.
    output_directory = "../all/rstst/"  # Update with your desired output directory.
    main(root_directory, output_directory, True)