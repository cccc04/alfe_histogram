import json
import os
import re
import matplotlib.pyplot as plt
from scipy.stats import fit, norm, skewnorm
import numpy as np
from datetime import datetime
import util
from typing import Dict, Any, List, Tuple

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

def load_existing_xlim(output_directory, impedance):
    xlim_file_path = os.path.join(output_directory, f"limits.json")
    if os.path.exists(xlim_file_path):
        with open(xlim_file_path, "r") as f:
            return json.load(f)  # Load existing xlim limits
    return {}  # Return an empty dictionary if no existing file is found

def _fit_distribution(values: List[float], use_skew: bool) -> Dict[str, Any]:
    """1. FIT: Fits data to a distribution and returns its parameters."""
    p10, p90 = np.percentile(values, [10, 90])
    filtered = [v for v in values if p10 <= v <= p90]
    if not filtered:
        return {"mu": 0, "sigma": 1, "a": 0, "loc": 0, "scale": 1, "label": "Fit Failed"}

    if use_skew:
        a, loc, scale = skewnorm.fit(filtered)
        label = f'Skew-Normal Fit\n$\\mu$={loc:.3g}, $\\sigma$={scale:.3g}'
        return {"mu": loc, "sigma": scale, "a": a, "loc": loc, "scale": scale, "label": label}
    else:
        mu, sigma = norm.fit(filtered)
        label = f'Gaussian Fit\n$\\mu$={mu:.3g}, $\\sigma$={sigma:.3g}'
        return {"mu": mu, "sigma": sigma, "a": 0, "loc": mu, "scale": sigma, "label": label}

def _prepare_canvas(xlim: Dict[str, float], config: Dict[str, Any]) -> Tuple[Any, Any, Any]:
    """2. PREPARE: Creates and returns the Matplotlib figure and axes."""
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.set_xlim(xlim["min"], xlim["max"])
    ax2 = ax1.twinx()
    ax2.set_yticks([]) # The twin axis is for scaling only
    
    # Set primary axis labels
    ax1.set_xlabel(config["x_axis_label"])
    ax1.set_ylabel('Count')
    ax1.grid(True)
    return fig, ax1, ax2

def _plot_on_canvas(
    ax1: Any, ax2: Any, plot_values: List[float], bins: Any,
    fit_params: Dict[str, Any], spec_limits: Dict[str, Any],
    essentials: Dict[str, str], config: Dict[str, Any]
):
    """3. PLOT: Draws all data, fits, and lines onto the prepared axes."""
    # Plot main histogram and the invisible scaling histogram
    color = config["color"]
    label = config["label"]
    ax1.hist(plot_values, bins=bins, alpha=0.7, label=label, color=color)
    ax2.hist(plot_values, bins=bins, alpha=0, density=True)

    # Plot the fitted curve
    if config["show_fit"]:
        x_fit = np.linspace(ax1.get_xlim()[0], ax1.get_xlim()[1], 1000)
        y_fit = (skewnorm.pdf(x_fit, fit_params["a"], fit_params["loc"], fit_params["scale"])
                 if config["use_skew"]
                 else norm.pdf(x_fit, fit_params["mu"], fit_params["sigma"]))
        ax2.plot(x_fit, y_fit, 'k--', color=color, label=fit_params["label"])

    # Plot specification limit lines
    if config["xlimb"] and essentials["full_key"] in spec_limits:
        lim = spec_limits[essentials["full_key"]]
        ax1.axvline(x=lim["min"], color='r', ls='--', label=f'Min: {lim["min"]:.3g}')
        ax1.axvline(x=lim["max"], color='r', ls='--', label=f'Max: {lim["max"]:.3g}')

def _finalize_and_save_plot(fig: Any, ax1: Any, ax2: Any, filepath: str, title: str):
    """4. SAVE: Sets final touches like title/legend, then saves and closes."""
    ax1.set_title(title)
    
    # Combine legends from both axes into one
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(filepath, dpi=300)
    plt.close(fig)

def plot_histograms(
    data_collection: Dict[str, Dict[str, Any]], output_directory: str, root_directory: str,
    impedance: str, label: str, key_prefix: str, xlimb: bool, show_fit: bool = True
):

    # --- Initial Setup ---
    spec_limits = load_existing_xlim(root_directory, impedance) if xlimb else {}

    channel_params_units = {
    "baseline": "Baseline (mV)",            
    "noise_rms_mv": "noise rms (mV)",
    "gain": "Gain ($\\Omega$)",         
    "eni": "ENI (nA)",                             
    "peaking_time": "Peaking Time (ns)",                   
    "max_non_linearity": "INL (%)",                 
    "fit_gain": "Fit Gain ($\\Omega$)",                    
    "gain_crude": "Gain Crude ($\\Omega$)",
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
    
    essentials = []
    plot_values = []
    bins = []
    fit_params = []
    plot_config = []
    xlim = []
    filepath = []
    i = 0
    for data_key, data_dict in data_collection.items():

        items_to_plot = {}
        for outer_key, inner_data in data_dict.items():
            if isinstance(inner_data, dict):
                items_to_plot.update({(outer_key, k): v for k, v in inner_data.items()})
            else:
                items_to_plot[(None, outer_key)] = inner_data
            
        # --- Main Loop ---
        j = 0
        essentials.append([])
        plot_values.append([])
        bins.append([])
        fit_params.append([])
        plot_config.append([])
        for (outer_key, param), values in items_to_plot.items():
            if not values:
                continue
        
            # --- Data Preparation Step ---
            essentials[i].append({ 
                "full_key": f"{outer_key or key_prefix}_{param}_{impedance}",
                "title": f"{param} for {outer_key}" if outer_key else f"{label} {param}"
            })
            filename = f"{essentials[i][j]['full_key']}_histogram.png".replace(f"_{key_prefix}", label.lower())
            if i == 0:
                filepath.append(os.path.join(output_directory, filename))
            if os.path.exists(filepath[j]):
                continue
            
            use_skew = 'uniformity' in essentials[i][j]["full_key"].lower()
            fit_params[i].append(_fit_distribution(values, use_skew))
        
            xlim_min = -0.05 if use_skew else fit_params[i][j]["mu"] - 6 * fit_params[i][j]["sigma"]
            xlim_max = fit_params[i][j]["mu"] + 6 * fit_params[i][j]["sigma"]
            if i == 0:
                xlim.append({"min": xlim_min, "max": xlim_max})
            else:
                xlim[j]["min"] = min(xlim[j]["min"], xlim_min)
                xlim[j]["max"] = max(xlim[j]["max"], xlim_max)
        
            plot_values[i].append([v for v in values if xlim[j]["min"] <= v <= xlim[j]["max"]])
            if not plot_values[i][j]:
                continue
            
            bin_width = (xlim_max - xlim_min) / N_BINS
            bins[i].append(np.linspace(xlim_min, xlim_max, N_BINS) if not xlimb
                    else np.arange(min(plot_values[i][j]), max(plot_values[i][j]) + bin_width, bin_width))
                    
            plot_config[i].append({
                "show_fit": show_fit, "use_skew": use_skew, "xlimb": xlimb, "label": data_key, "color": 'C0',
                "x_axis_label": channel_params_units.get(param, param)
            })
            j += 1
        
        i += 1


    # 1. Prepare the canvas
    for jj in range(0, j):
        fig, ax1, ax2 = _prepare_canvas(xlim[jj], plot_config[0][jj])

        for ii in range(0, i):
            # 2. Plot all data onto the canvas
            _plot_on_canvas(ax1, ax2, plot_values[ii][jj], bins[ii][jj], fit_params[ii][jj], spec_limits, essentials[ii][jj], plot_config[ii][jj])
        
        # 3. Finalize and save the plot
        _finalize_and_save_plot(fig, ax1, ax2, filepath[jj], essentials[0][jj]["title"] + " - " + impedance)


def main(root_directorys: Dict[str, any], output_directory, xlimb = False):
    impedance = ["25", "50"]
    current_directory = "./"
    for impedance_index in impedance:
        os.makedirs(output_directory, exist_ok=True)
   
        # Collect all results_all.json file paths.
        channel_values = {}
        power_ldo_values = {}
        uniformity_hg = {}
        uniformity_lg = {}
        gain_ratio_values = {}
        for label, root_directory in root_directorys.items():
            file_paths = []
            for dirpath, _, filenames in os.walk(root_directory):
                if "results_all.json" in filenames:
                    file_paths.append(os.path.join(dirpath, "results_all.json"))
        
            file_paths = sorted(file_paths, key=util.extract_timestamp, reverse=True)
            channel_values[label], power_ldo_values[label], uniformity_hg[label], uniformity_lg[label], gain_ratio_values[label] = read_json_files(file_paths, impedance_index)
   
        plot_histograms(channel_values, output_directory, current_directory, impedance_index, "Channel", "channel", "channel_histograms", xlimb)
        plot_histograms(power_ldo_values, output_directory, current_directory, impedance_index, "Power_LDO", "power_ldo", "power_ldo_histograms", xlimb)
        plot_histograms(uniformity_hg, output_directory, current_directory, impedance_index, "HG", "hg", "uniformity_histograms", xlimb)
        plot_histograms(uniformity_lg, output_directory, current_directory, impedance_index, "LG", "lg", "uniformity_histograms", xlimb)
        plot_histograms(gain_ratio_values, output_directory, current_directory, impedance_index, "Gain_Ratio", "gain_ratio", "gain_ratio_histograms", xlimb)

if __name__ == '__main__':
    root_directory = {"robot": "../July/", "manual": "../0603_0611/"}  # Update with your actual root directory.
    output_directory = "../July/rstst6/"  # Update with your desired output directory.
    main(root_directory, output_directory, True)