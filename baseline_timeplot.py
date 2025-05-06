import json
import os
import matplotlib.pyplot as plt
import numpy as np
import datetime
import matplotlib.dates as mdates

def read_json_file(file_paths):
    impedance = "25"
	# Define per-channel parameters (excluding uniformity)
    channel_params = [
        "baseline", "noise_rms_mv", "gain", "eni", 
        "peaking_time", "max_non_linearity", "i2c_margin_list"
    ]
    
    # List of channels found in the JSON files
    channels = [
        "CH0 HG", "CH1 HG", "CH2 HG", "CH3 HG", 
        "CH0 LG", "CH1 LG", "CH2 LG", "CH3 LG", 
        "SUM x3", "SUM x1",
    ]

    channel_values = {channel: {param: [] for param in channel_params} for channel in channels}
    power_ldo_values = {}
    gain_ratio_values = {0: [], 1: [], 2: [], 3: []}
    uniformity_hg = {"gain_uniformity": [], "peaking_time_uniformity": [], "baseline_uniformity": []}
    uniformity_lg = {"gain_uniformity": [], "peaking_time_uniformity": [], "baseline_uniformity": []}
    hour_values = []
    temp_values = []

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
            if "test_time" in data:
                raw_time = data["test_time"]
            else:
                print("Key 'test_time' not found in data")
                continue
            if "board_temp" in data:
                temps = data["board_temp"].values()  # dict_values([24.10938, 23.50781])
                temp = sum(temps) / len(temps)
            else:
                print("Key 'board_temp' not found in data")
                continue
            process_results(data, f"results_noise_{impedance}_all_ch_HG", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
            process_results(data, f"results_noise_{impedance}_all_ch_LG", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
            process_results(data, f"results_noise_{impedance}_sum_x3", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
            process_results(data, f"results_noise_{impedance}_sum_x1", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"])
            process_results(data, f"results_linearity_{impedance}_sum_x3", ["max_non_linearity"])
            process_results(data, f"results_linearity_{impedance}_sum_x1", ["max_non_linearity"])
            process_results(data, f"results_linearity_{impedance}_all_ch_HG", ["max_non_linearity"])
            process_results(data, f"results_linearity_{impedance}_all_ch_LG", ["max_non_linearity"])
            results = data[f"results_noise_{impedance}_all_ch_HG"]
            for key in uniformity_hg:
                uniformity_hg[key].append(results.get(key))
            results = data[f"results_noise_{impedance}_all_ch_LG"]
            for key in uniformity_lg:
                uniformity_lg[key].append(results.get(key))
            gain_ratio_key = f"gain_ratio_{impedance}"
            if gain_ratio_key in data:
                results = data[gain_ratio_key]
                if isinstance(results, list):
                    for idx, value in enumerate(results):
                        if idx in gain_ratio_values:
                            gain_ratio_values[idx].append(value)
                else:
                    print(f"Warning: Expected a list for {gain_ratio_key}, but found {type(results)}")
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

            cleaned = raw_time.replace('_T_', ' ').replace('_', '-')
            # Parse datetime in the format "dd-mm-yy HH-MM-SS"
            dt = datetime.datetime.strptime(cleaned, "%d-%m-%y %H-%M-%S")
            hour_values.append(dt)
            temp_values.append(temp)

    return channel_values, hour_values, temp_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values

def plot_baseline_timeplot(channel_values, hour_values, y, output_directory):
    for channel, values in channel_values.items():
        if not isinstance(values, dict):
            values = {channel: values}
            channel = None
        for param, value in values.items():
            if value:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(hour_values, value, 'o')  # 'o' for dots
                if len(str(param)) < 2:
                    param = "gain_ratio" + str(param)
                ax.set_ylabel(f"{param}")
                if y:
                    ax.set_xlabel("Time", fontsize=12)
                    if channel == None:
                        ax.set_title(f"{param} Time Plot", fontsize=14)
                    else:                        
                        ax.set_title(f"{param} Time Plot - {channel}", fontsize=14)
                    ax.xaxis.set_major_locator(mdates.AutoDateLocator())  # Auto adjusts tick frequency
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))  # Format as date
                    plt.xticks(rotation=10)  # Rotate the date labels for better readability
                else:
                    ax.set_xlabel("Temperature")
                    if channel == None:
                        ax.set_title(f"{param} Temperature Plot")
                    else:
                        ax.set_title(f"{param} Temperature Plot - {channel}")
                ax.grid(True)

                if y:
                    plt.savefig(os.path.join(output_directory, f"{param}_timeplot_{channel}.png"), dpi=300)
                else:
                    plt.savefig(os.path.join(output_directory, f"{param}_tempplot_{channel}.png"), dpi=300)
                plt.close(fig)  # Close this figure after saving

if __name__ == '__main__':
    # Example usage
    root_directory = "../BNL_Tray1_Tray4_Tray2_tray3_674/Nevis_Tray2_Tray3_355/GradeA_Tray3_173"
    output_directory = "../BNL_Tray1_Tray4_Tray2_tray3_674/t3/"
    # Collect all results_all.json file paths.
    file_paths = []
    for dirpath, _, filenames in os.walk(root_directory):
        if "results_all.json" in filenames:
            file_paths.append(os.path.join(dirpath, "results_all.json"))
    channel_values, hour_values, temp_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values = read_json_file(file_paths)
    plot_baseline_timeplot(channel_values, hour_values, True, output_directory)
    plot_baseline_timeplot(channel_values, temp_values, False, output_directory)
    plot_baseline_timeplot(power_ldo_values, hour_values, True, output_directory)
    plot_baseline_timeplot(power_ldo_values, temp_values, False, output_directory)
    plot_baseline_timeplot(uniformity_hg, hour_values, True, output_directory)
    plot_baseline_timeplot(uniformity_hg, temp_values, False, output_directory)
    plot_baseline_timeplot(uniformity_lg, hour_values, True, output_directory)
    plot_baseline_timeplot(uniformity_lg, temp_values, False, output_directory)
    plot_baseline_timeplot(gain_ratio_values, hour_values, True, output_directory)
    plot_baseline_timeplot(gain_ratio_values, temp_values, False, output_directory)