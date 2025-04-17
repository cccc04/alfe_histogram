import json
import os
import matplotlib.pyplot as plt
import numpy as np

# Fixed bin size (e.g., 20 bins)
BIN_SIZE = 20

def read_json_files(file_paths, entry, criteria_file_path):
    # Load criteria from the JSON file
    with open(criteria_file_path, 'r') as f:
        criteria = json.load(f)

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
   
    # Dictionary for power_ldo data (if available)
    power_ldo_values = {}

    # Initialize gain_ratio_values as a dictionary with 4 lists (one per gain ratio value)
    gain_ratio_values = {0: [], 1: [], 2: [], 3: []}
   
    # Dictionaries to store uniformity values separately for HG and LG (global, one value per file)
    uniformity_hg = {"gain_uniformity": [], "peaking_time_uniformity": []}
    uniformity_lg = {"gain_uniformity": [], "peaking_time_uniformity": []}
    def is_within_criteria(value, key, criteria):
        """Check if the value is within the specified criteria."""
        if key in criteria:
            min_val = criteria[key]["min"]
            max_val = criteria[key]["max"]
            return min_val <= value <= max_val
        return True  # If the key isn't in the criteria, don't apply any check

    # Helper for processing keys that do not include uniformity parameters
    def process_results(data, entry, key_suffix, params, criteria, channel_values, buffer, reset_flag):
        if key_suffix in data:
            results = data[key_suffix]
            channel_list = results.get("channel_list", results.get("i2c_frequency_list", None))
            if not channel_list:
                print(f"Warning: Neither 'channel_list' nor 'i2c_frequency_list' found in {key_suffix}")
                return reset_flag
            for idx, channel in enumerate(channel_list):
                for param in params:
                    if param in results:
                        value = results[param]
                        if isinstance(value, list):
                            try:
                                val = value[idx]
                            except IndexError:
                                print(f"Warning: Index error for {param} in {key_suffix}")
                                continue
                        else:
                            val = value
                        
                        # Check if the value is within the acceptable range from criteria
                        criteria_key = f"{channel}_{param}"
                        if not is_within_criteria(val, criteria_key, criteria):
                            print(f"Warning: {criteria_key} out of range, skipping file.")
                            #return True  # Mark to reset all previously passed data for this file
                        buffer[channel][param].append(val)
        return reset_flag
   
    for file_path in file_paths:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
            # Temporary buffer to store values for the current file
            temp_buffer = {channel: {param: [] for param in channel_params} for channel in channels}
            power_ldo_buffer = {}
            gain_ratio_buffer = {0: [], 1: [], 2: [], 3: []}
            uniformity_hg_buffer = {"gain_uniformity": [], "peaking_time_uniformity": []}
            uniformity_lg_buffer = {"gain_uniformity": [], "peaking_time_uniformity": []}
            reset_flag = False  # Flag to track if any validation failed

            # Process HG key and extract HG uniformity if present
            key_hg = f"results_noise_{entry}_all_ch_HG"
            reset_flag = process_results(data, entry, key_hg, ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"], criteria, channel_values, temp_buffer, reset_flag)
            if reset_flag:
                continue  # Skip this file if it failed validation
            
            # Extract uniformity parameters for HG (only once per file)
            if key_hg in data:
                results = data[key_hg]
                if "gain_uniformity" in results:
                    uniformity_hg_buffer["gain_uniformity"].append(results["gain_uniformity"])
                if "peaking_time_uniformity" in results:
                    uniformity_hg_buffer["peaking_time_uniformity"].append(results["peaking_time_uniformity"])

            # Process LG key and extract LG uniformity if present
            key_lg = f"results_noise_{entry}_all_ch_LG"
            reset_flag = process_results(data, entry, key_lg, ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"], criteria, channel_values, temp_buffer, reset_flag)
            if reset_flag:
                continue  # Skip this file if it failed validation
            
            # Extract uniformity parameters for LG (only once per file)
            if key_lg in data:
                results = data[key_lg]
                if "gain_uniformity" in results:
                    uniformity_lg_buffer["gain_uniformity"].append(results["gain_uniformity"])
                if "peaking_time_uniformity" in results:
                    uniformity_lg_buffer["peaking_time_uniformity"].append(results["peaking_time_uniformity"])

            # Process additional noise keys (which don't include uniformity)
            reset_flag = process_results(data, entry, f"results_noise_{entry}_sum_x3", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"], criteria, channel_values, temp_buffer, reset_flag)
            if reset_flag:
                continue  # Skip this file if it failed validation
            reset_flag = process_results(data, entry, f"results_noise_{entry}_sum_x1", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"], criteria, channel_values, temp_buffer, reset_flag)
            if reset_flag:
                continue  # Skip this file if it failed validation
           
            # Process linearity results
            reset_flag = process_results(data, entry, f"results_linearity_{entry}_sum_x3", ["max_non_linearity", "fit_gain"], criteria, channel_values, temp_buffer, reset_flag)
            if reset_flag:
                continue  # Skip this file if it failed validation
            reset_flag = process_results(data, entry, f"results_linearity_{entry}_sum_x1", ["max_non_linearity", "fit_gain"], criteria, channel_values, temp_buffer, reset_flag)
            if reset_flag:
                continue  # Skip this file if it failed validation
            reset_flag = process_results(data, entry, f"results_linearity_{entry}_all_ch_HG", ["max_non_linearity", "fit_gain"], criteria, channel_values, temp_buffer, reset_flag)
            if reset_flag:
                continue  # Skip this file if it failed validation
            reset_flag = process_results(data, entry, f"results_linearity_{entry}_all_ch_LG", ["max_non_linearity", "fit_gain"], criteria, channel_values, temp_buffer, reset_flag)
            if reset_flag:
                continue  # Skip this file if it failed validation
           
            process_results(data, entry, f"results_channel_enable_{entry}", ["gain_crude"], criteria, channel_values, temp_buffer, reset_flag)
            process_results(data, entry, f"i2c_results", ["i2c_margin_list"], criteria, channel_values, temp_buffer, reset_flag)

            # Process gain_ratio_{entry} independently, expecting a list of 4 values per file.
            gain_ratio_key = f"gain_ratio_{entry}"
            if gain_ratio_key in data:
                results = data[gain_ratio_key]
               
                if isinstance(results, list):
                    if len(results) != 4:
                        print(f"Warning: Expected 4 gain_ratio values but got {len(results)} in {file_path}")
                    for idx, value in enumerate(results):
                        if idx in gain_ratio_buffer:
                            criteria_key = f"{idx}"
                            if not is_within_criteria(value, criteria_key, criteria):
                                print(f"Warning: {criteria_key} out of range, skipping file.")
                                #reset_flag = True  # Mark to reset all previously passed data for this file
                                #break  # Breaks out of the inner loop, but not the outer loop
                            gain_ratio_buffer[idx].append(value)
                else:
                    print(f"Warning: Expected a list for {gain_ratio_key}, but found {type(results)}")
           
            # Process power_ldo data if available
            if "power_ldo" in data:
                for ldo in data["power_ldo"]:
                    ldo_name = ldo.get("name")
                    if not ldo_name:
                        continue
                    if ldo_name not in power_ldo_buffer:
                        power_ldo_buffer[ldo_name] = {}
                    for key, value in ldo.items():
                        if key == "name":
                            continue
                        if key not in power_ldo_buffer[ldo_name]:
                            power_ldo_buffer[ldo_name][key] = []
                        criteria_key = f"{ldo_name}_{key}"
                        if not is_within_criteria(value, criteria_key, criteria):
                            print(f"Warning: {criteria_key} out of range, skipping file.")
                            #reset_flag = True  # Mark to reset all previously passed data for this file
                            #break  # Breaks out of the inner loop, but not the outer loop
                        power_ldo_buffer[ldo_name][key].append(value)
                    if reset_flag:
                        break  # Breaks out of the outer loop to skip processing this file

            # Now that all checks are passed, append the buffered values to the main storage
            if not reset_flag:
                for channel in channels:
                    for param in channel_params:
                        channel_values[channel][param].extend(temp_buffer[channel][param])
                for ldo_name, ldo_data in power_ldo_buffer.items():
                    if ldo_name not in power_ldo_values:
                        power_ldo_values[ldo_name] = {}

                    for key, values in ldo_data.items():
                        if key not in power_ldo_values[ldo_name]:
                            power_ldo_values[ldo_name][key] = []

                        power_ldo_values[ldo_name][key].extend(values)
                # Process uniformity data (HG and LG)
                if uniformity_hg_buffer["gain_uniformity"]:
                    uniformity_hg["gain_uniformity"].extend(uniformity_hg_buffer["gain_uniformity"])
                if uniformity_hg_buffer["peaking_time_uniformity"]:
                    uniformity_hg["peaking_time_uniformity"].extend(uniformity_hg_buffer["peaking_time_uniformity"])
                if uniformity_lg_buffer["gain_uniformity"]:
                    uniformity_lg["gain_uniformity"].extend(uniformity_lg_buffer["gain_uniformity"])
                if uniformity_lg_buffer["peaking_time_uniformity"]:
                    uniformity_lg["peaking_time_uniformity"].extend(uniformity_lg_buffer["peaking_time_uniformity"])
                for idx, values in gain_ratio_buffer.items():
                    gain_ratio_values[idx].extend(values)
    
   
    return channel_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values

def print_statistics(data, label=None):
    if not data:
        print("No data to display.\n")
        return

    # Case 1: flat dict of lists
    if isinstance(next(iter(data.values())), list):
        for param, values in data.items():
            if values:
                arr = np.array(values)
                label_text = f"{label} " if label else ""
                print(f"{label_text}{param}: Mean = {np.mean(arr):.4f}, Std = {np.std(arr):.4f}")
        print()
        return

    # Case 2: Nested dict (e.g., per-channel or power_ldo)
    for group, params in data.items():
        group_label = f"{label} {group}" if label else f"{group}"
        print(f"{group_label}:")
        for param, values in params.items():
            if values:
                arr = np.array(values)
                print(f"  {param}: Mean = {np.mean(arr):.4f}, Std = {np.std(arr):.4f}")
        print()

def save_current_bin_widths(channel_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values, output_directory, filename="bin_widths.json", bin_size=BIN_SIZE):
    """
    Calculate and save the bin width for each parameter histogram to a JSON file.
    """
    bin_widths = {}
   
    # Channel histograms
    channel_bin_widths = {}
    for channel, params in channel_values.items():
        for param, values in params.items():
            if values:
                try:
                    width = (max(values) - min(values)) / bin_size
                except Exception:
                    width = None
                channel_bin_widths[f"{channel}_{param}"] = width
    bin_widths["channel_histograms"] = channel_bin_widths

    # power_ldo histograms
    power_ldo_bin_widths = {}
    for ldo, params in power_ldo_values.items():
        for param, values in params.items():
            if values:
                try:
                    width = (max(values) - min(values)) / bin_size
                except Exception:
                    width = None
                power_ldo_bin_widths[f"{ldo}_{param}"] = width
    bin_widths["power_ldo_histograms"] = power_ldo_bin_widths

    # Uniformity histograms (HG and LG)
    uniformity_bin_widths = {}
    for label, uniformity in zip(["HG", "LG"], [uniformity_hg, uniformity_lg]):
        for param, values in uniformity.items():
            if values:
                try:
                    width = (max(values) - min(values)) / bin_size
                except Exception:
                    width = None
                uniformity_bin_widths[f"{label}_{param}"] = width
    bin_widths["uniformity_histograms"] = uniformity_bin_widths

    # Gain ratio histograms
    gain_ratio_bin_widths = {}
    for idx, values in gain_ratio_values.items():
        if values:
            try:
                width = (max(values) - min(values)) / bin_size
            except Exception:
                width = None
            gain_ratio_bin_widths[f"gain_ratio_{idx}"] = width
    bin_widths["gain_ratio_histograms"] = gain_ratio_bin_widths

    # Save to JSON
    file_path = os.path.join(output_directory, filename)
    with open(file_path, "w") as f:
        json.dump(bin_widths, f, indent=4)
    print(f"Bin widths saved to {file_path}")

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

    if not xlimb:
        xlim_file_path = os.path.join(output_directory, f"{entry}_xlim_limits.json")
        with open(xlim_file_path, "w") as f:
            json.dump(xlim_limits, f, indent=4)


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
   
        channel_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values = read_json_files(file_paths, entry, current_directory + entry + "_xlim_limits_dummy.json")
   
        print_statistics(channel_values)
        print_statistics(power_ldo_values)
        print_statistics(uniformity_hg, "HG")
        print_statistics(uniformity_lg, "LG")
        print_statistics(gain_ratio_values)
   
        # Save current bin widths to a JSON file.
        #save_current_bin_widths(channel_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values, output_directory, entry + "widths.json")
   
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
    output_directory = "../BNL_Tray1_Tray4_Tray2_tray3_674/rs2/"  # Update with your desired output directory.
    main(root_directory, output_directory, True, True)