import json
import os
import matplotlib.pyplot as plt
import numpy as np

# Fixed bin size (e.g., 20 bins)
BIN_SIZE = 20

def read_json_files(file_paths, entry):
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
    uniformity_hg = {"gain_uniformity": [], "peaking_time_uniformity": []}
    uniformity_lg = {"gain_uniformity": [], "peaking_time_uniformity": []}

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

    for file_path in file_paths:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Process HG
        key_hg = f"results_noise_{entry}_all_ch_HG"
        process_results(data, key_hg, ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
        if key_hg in data:
            results = data[key_hg]
            uniformity_hg["gain_uniformity"].append(results.get("gain_uniformity"))
            uniformity_hg["peaking_time_uniformity"].append(results.get("peaking_time_uniformity"))

        # Process LG
        key_lg = f"results_noise_{entry}_all_ch_LG"
        process_results(data, key_lg, ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
        if key_lg in data:
            results = data[key_lg]
            uniformity_lg["gain_uniformity"].append(results.get("gain_uniformity"))
            uniformity_lg["peaking_time_uniformity"].append(results.get("peaking_time_uniformity"))

        # Process sum and linearity data
        process_results(data, f"results_noise_{entry}_sum_x3", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
        process_results(data, f"results_noise_{entry}_sum_x1", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
        process_results(data, f"results_linearity_{entry}_sum_x3", ["max_non_linearity", "fit_gain"])
        process_results(data, f"results_linearity_{entry}_sum_x1", ["max_non_linearity", "fit_gain"])
        process_results(data, f"results_linearity_{entry}_all_ch_HG", ["max_non_linearity", "fit_gain"])
        process_results(data, f"results_linearity_{entry}_all_ch_LG", ["max_non_linearity", "fit_gain"])
        process_results(data, f"results_channel_enable_{entry}", ["gain_crude"])
        process_results(data, "i2c_results", ["i2c_margin_list"])

        # Gain ratio
        gain_ratio_key = f"gain_ratio_{entry}"
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

def load_existing_xlim(output_directory, entry):
    xlim_file_path = os.path.join(output_directory, f"{entry}_xlim_limits.json")
    if os.path.exists(xlim_file_path):
        with open(xlim_file_path, "r") as f:
            return json.load(f)  # Load existing xlim limits
    return {}  # Return an empty dictionary if no existing file is found

def plot_histograms(data_dict, output_directory, root_directory, entry, label, key_prefix, histogram_type, custom_bin_widths, xlimb):
    if xlimb:
        xlim_limits = load_existing_xlim(root_directory, entry)
    else:
        xlim_limits = load_existing_xlim(output_directory, entry)

    for outer_key, inner_dict in data_dict.items():
        # Handle cases where data_dict is flat like uniformity/gain_ratio
        if not isinstance(inner_dict, dict):
            inner_dict = {outer_key: inner_dict}
            outer_key = None  # No need to prefix filenames with outer_key

        for param, values in inner_dict.items():
            if values:
                plt.figure(figsize=(10, 6))
                full_key = f"{key_prefix}_{param}" if outer_key is None else f"{outer_key}_{param}"
                bw = None

                if custom_bin_widths:
                    bw = custom_bin_widths.get(histogram_type, {}).get(full_key)

                bins = np.arange(min(values), max(values) + bw, bw) if bw else BIN_SIZE
                plt.hist(values, bins=bins, alpha=0.7)

                if xlimb:
                    if full_key in xlim_limits:
                        xlim = xlim_limits[full_key]
                        plt.xlim(xlim["min"] - 0.125*(xlim["max"] - xlim["min"]),
                                 xlim["max"] + 0.125*(xlim["max"] - xlim["min"]))
                        plt.axvline(x=xlim["min"], color='red', linestyle='--', label=f'{param} min')
                        plt.axvline(x=xlim["max"], color='red', linestyle='--', label=f'{param} max')

                        # Get y-axis limits to position text just below the x-axis
                        ymin, ymax = plt.ylim()
                        ytext_pos = ymin - 0.05 * (ymax - ymin)  # slightly below the x-axis

                        # Add text at bottom of the vertical lines
                        plt.text(xlim["min"], ytext_pos, f'{xlim["min"]:.2f}', color='red',
                                 ha='center', va='top', fontsize=9, clip_on=False)
                        plt.text(xlim["max"], ytext_pos, f'{xlim["max"]:.2f}', color='red',
                                 ha='center', va='top', fontsize=9, clip_on=False)
                    else:
                        print(f"xlim for {full_key} does not exist in file")
                else:
                    xlim_limits[full_key] = {
                        "min": plt.gca().get_xlim()[0],
                        "max": plt.gca().get_xlim()[1]
                    }

                title_key = f"{label} {param}" if outer_key is None else f"{param} for {outer_key}"
                plt.title(f"{title_key} - {entry}")
                plt.xlabel(param)
                plt.ylabel("Count")
                plt.grid(True)
                plt.tight_layout()

                filename = f"{label.lower()}_{param}_{entry}_histogram.png" if outer_key is None \
                    else f"{outer_key}_{param}_{entry}_histogram.png"
                plt.savefig(os.path.join(output_directory, filename))
                plt.close()


def main(root_directory, output_directory, bwcustom = False, xlimb = False):
    entryv = ["25", "50"]
    current_directory = "./"
    for entry in entryv:
        os.makedirs(output_directory, exist_ok=True)
   
        # Collect all results_all.json file paths.
        file_paths = []
        for dirpath, _, filenames in os.walk(root_directory):
            if "results_all.json" in filenames:
                file_paths.append(os.path.join(dirpath, "results_all.json"))
   
        channel_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values = read_json_files(file_paths, entry)
      
        # Optionally, load the bin widths for use in plotting.
        if bwcustom:
            custom_bin_widths = load_bin_widths(current_directory, entry + "widths.json")
        else:
            custom_bin_widths = None
   
        plot_histograms(channel_values, output_directory, current_directory, entry, "Channel", "channel", "channel_histograms", custom_bin_widths, xlimb)
        plot_histograms(power_ldo_values, output_directory, current_directory, entry, "Power_LDO", "power_ldo", "power_ldo_histograms", custom_bin_widths, xlimb)
        plot_histograms(uniformity_hg, output_directory, current_directory, entry, "HG", "hg", "uniformity_histograms", custom_bin_widths, xlimb)
        plot_histograms(uniformity_lg, output_directory, current_directory, entry, "LG", "lg", "uniformity_histograms", custom_bin_widths, xlimb)
        plot_histograms(gain_ratio_values, output_directory, current_directory, entry, "Gain_Ratio", "gain_ratio", "gain_ratio_histograms", custom_bin_widths, xlimb)

if __name__ == '__main__':
    root_directory = "../BNL_Tray1_Tray4_Tray2_tray3_674/"  # Update with your actual root directory.
    output_directory = "../BNL_Tray1_Tray4_Tray2_tray3_674/rstst/"  # Update with your desired output directory.
    main(root_directory, output_directory, True, True)