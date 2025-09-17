import json
import os
import re
import matplotlib.pyplot as plt
from scipy.stats import norm, skewnorm
import numpy as np
from datetime import datetime
import util

# Fixed number of bins (e.g., 20 bins)
N_BINS = 20

def read_json_files(file_paths, impedance):
    # Define per-channel parameters (excluding uniformity)
    channel_params = [
        "baseline", "noise_rms_mv", "gain", "eni", 
        "peaking_time", "max_non_linearity", "fit_gain", 
        "gain_crude", "i2c_margin_list", "i2c_phase_list"
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

    for file_path in file_paths:
        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {file_path}: {e}")
                continue
                
        if "test_time" in data:

            date_parts = data["test_time"].split('_')[:3]  # ['13', '06', '25']
            date_str = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"  # '13-06-25'
            date_obj = datetime.strptime(date_str, "%d-%m-%y")  # dd-mm-yy

            # Define cutoff date (e.g., June 7, 2025)
            cutoff_date = datetime(year=date_obj.year, month=6, day=7)

            # Check if it's later
            if date_obj < cutoff_date:
                print(f"skipping file")
                continue
        else:
            print(f"Warning: 'test_time' not found in {file_path}, skipping file")
            continue

        match = re.search(r'(\d{3}-\d{5})', file_path)
        if not match:
            match = re.search(r'(\d{3}-\s\d{5})', file_path)  # Handle cases with space
        if match:
            if match.group(1) not in s_n:
                s_n.append(match.group(1))
            else:
                print(f"({file_path}): Duplicate serial number {match.group(1)} found")
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
        process_results(data, "i2c_results", ["i2c_margin_list", "i2c_phase_list"])

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

def plot_histograms(data_dict, output_directory, root_directory, impedance, label, key_prefix, histogram_type, xlimb, show_fit=True):
    if xlimb:
        lim_limits = load_existing_xlim(root_directory, impedance)
    
    channel_params_with_units = {
    "baseline": "Baseline (mV)",            
    "noise_rms_mv": "noise rms (mV)",
    "gain": "Gain ($\Omega$)",         
    "eni": "ENI (nA)",                             
    "peaking_time": "Peaking Time (ns)",                   
    "max_non_linearity": "INL (%)",                 
    "fit_gain": "Fit Gain ($\Omega$)",                    
    "gain_crude": "Gain Crude ($\Omega$)",
    "gain_uniformity": "Gain Uniformity (%)",
    "peaking_time_uniformity": "Peaking Time Uniformity (%)",
    "baseline_uniformity": "Baseline Uniformity (%)",
    "i2c_frequency_list": "I2C Frequency (kHz)",
    0: "Gain Ratio",
    2: "Gain Ratio",
    1: "Gain Ratio",
    3: "Gain Ratio",
    "voltage": "Voltage (mV)",
    "current": "Current (mA)",
    "i2c_margin_list": "dB",  
    }
    for outer_key, inner_dict in data_dict.items():
        if not isinstance(inner_dict, dict):
            inner_dict = {outer_key: inner_dict}
            outer_key = None

        for param, values in inner_dict.items():
            if values:
                fig, ax1 = plt.subplots(figsize=(10, 6))
                full_key = f"{key_prefix}_{param}_{impedance}" if outer_key is None else f"{outer_key}_{param}_{impedance}"

                filename = f"{label.lower()}_{param}_{impedance}_histogram.png" if outer_key is None \
                    else f"{outer_key}_{param}_{impedance}_histogram.png"

                if os.path.exists(os.path.join(output_directory, filename)):
                    plt.close()
                    continue

                use_skew = 'uniformity' in full_key.lower()
                
                p5, p95 = np.percentile(values, [10, 90])
                filtered = [v for v in values if p5 <= v <= p95]
                if use_skew:
                    a, loc, scale = skewnorm.fit(filtered)
                    fit_label = f'Skew-Normal Fit\n$\mu$={loc:.3g}, $\sigma$={scale:.3g}'
                    mu, sigma = loc, scale  # For setting x-limits
                else:
                    mu, sigma = norm.fit(filtered)
                    fit_label = f'Gaussian Fit\n$\mu$={mu:.3g}, $\sigma$={sigma:.3g}'
                

                # Default bin width and bins
                bw = None
                bins = N_BINS

                if xlimb and full_key in lim_limits:
                    lim = lim_limits[full_key]

                if use_skew:
                    xlim = {
                        "min": -0.05,
                        "max": mu + 6 * sigma
                    }
                else:
                    xlim = {
                        "min": mu - 6 * sigma,
                        "max": mu + 6 * sigma
                    }
                
                bw = (xlim["max"] - xlim["min"]) / (N_BINS)

                values = [v for v in values if xlim["min"] <= v <= xlim["max"]]

                if max(values) - min(values) > 20000 * bw:
                    print(f"Warning: Large range in values for {full_key}. Consider adjusting bin width.")
                    continue

                bins = np.arange(min(values), max(values) + bw, bw)

                if not xlimb:
                    bins = np.linspace(xlim["min"], xlim["max"], N_BINS)

                # X limits and vertical lines
                plt.xlim(xlim["min"] ,
                         xlim["max"] )

                # Plot histogram
                counts, bins_, patches = ax1.hist(values, bins=bins, alpha=0.7, density=False, label='Count')
                ax1.set_ylabel('Count')
                ax1.set_xlabel(channel_params_with_units.get(param, param))
                ax1.tick_params(axis='y')
                ax1.grid(True)

                ax2 = ax1.twinx()
                ax2.hist(values, bins=bins, alpha=0, density=True)  # invisible histogram for scaling
                ax2.set_yticks([])  

                # Gaussian curve
                if show_fit and not use_skew:
                    x = np.linspace(xlim["min"], xlim["max"], 1000)
                    y = skewnorm.pdf(x, a, loc, scale) if use_skew else norm.pdf(x, mu, sigma)
                    ax2.plot(x, y, 'k--', label=fit_label)

                if xlimb and full_key in lim_limits:
                    plt.axvline(x=lim["min"], color='red', linestyle='--', label=f'min: {lim["min"]:.2f}')
                    plt.axvline(x=lim["max"], color='red', linestyle='--', label=f'max: {lim["max"]:.2f}')
                elif xlimb:
                    print(f"xlim for {full_key} does not exist in file")

                title_key = f"{label} {param}" if outer_key is None else f"{param} for {outer_key}"
                plt.title(f"{title_key} - {impedance}")
                plt.grid(True)
                plt.legend(loc='upper right', fontsize=12)
                plt.tight_layout()

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
        
        file_paths = sorted(file_paths, key=util.extract_timestamp, reverse=True)
        channel_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values = read_json_files(file_paths, impedance_index)
   
        plot_histograms(channel_values, output_directory, current_directory, impedance_index, "Channel", "channel", "channel_histograms", xlimb)
        plot_histograms(power_ldo_values, output_directory, current_directory, impedance_index, "Power_LDO", "power_ldo", "power_ldo_histograms", xlimb)
        plot_histograms(uniformity_hg, output_directory, current_directory, impedance_index, "HG", "hg", "uniformity_histograms", xlimb)
        plot_histograms(uniformity_lg, output_directory, current_directory, impedance_index, "LG", "lg", "uniformity_histograms", xlimb)
        plot_histograms(gain_ratio_values, output_directory, current_directory, impedance_index, "Gain_Ratio", "gain_ratio", "gain_ratio_histograms", xlimb)

if __name__ == '__main__':
    root_directory = "../July/"  # Update with your actual root directory.
    output_directory = "../July/rstst3/"  # Update with your desired output directory.
    main(root_directory, output_directory, True)