import json
from socket import gaierror
import pandas as pd
import re
import os
from collections import defaultdict

def apply_cuts(file_paths, criteria_file_path, output_file_path):
    # Load criteria from the JSON file
    
    with open(criteria_file_path, 'r') as f:
        criteria = json.load(f)

    output = []
    pass_count = 0
    fail_count = 0
    param_stats = defaultdict(lambda: {"pass": 0, "fail": 0})

    def is_within_criteria(value, key, criteria):
        """Check if the value is within the specified criteria."""
        if key in criteria:
            min_val = criteria[key]["min"]
            max_val = criteria[key]["max"]
            return min_val <= value <= max_val
        else:
            print(f"{key} not in criteria")
        return True  

    def process_results(data, key_suffix, params, impedance):
        row = []
        flag = False
        g = key_suffix.split("_")[-1]
        if key_suffix in data:
            results = data[key_suffix]
            channel_list = results.get("channel_list", results.get("i2c_frequency_list", None))
            if not channel_list:
                print(f"Warning: Neither 'channel_list' nor 'i2c_frequency_list' found in {key_suffix}")
                return
            failed = {}
            for idx, channel in enumerate(channel_list):
                for param in params:
                    if param in results:
                        if param not in failed:
                            failed[param] = False
                        value = results[param]
                        val = value[idx] if isinstance(value, list) else value
                        criteria_key = f"{channel}_{param}_{impedance}"
                        if not is_within_criteria(val, criteria_key, criteria):
                            row.append(f"{criteria_key}: {val}")
                            flag = True
                            if not failed[param]:
                                failed[param] = True
                                param_stats[f"{param}_{impedance}_{g}"]["fail"] += 1
            for param, failed in failed.items():
                if not failed:
                    param_stats[f"{param}_{impedance}_{g}"]["pass"] += 1
        else:
            for param in params:
                param_stats[f"{param}_{impedance}_{g}"]["fail"] += 1

        return row, flag

    uniformity_key = {"gain_uniformity", "peaking_time_uniformity", "baseline_uniformity"}
    gain_ratio_key = {0, 1, 2, 3}
    s_n = []

    for file_path in file_paths:
        row = []
        flag = False

        with open(file_path, 'r') as f:
            data = json.load(f)

        match = re.search(r'(\d{3}\d{5})', file_path)
        if not match:
            match = re.search(r'(\d{3}\d{5})', file_path)
        if match:
            if match.group(1) not in s_n:
                s_n.append(match.group(1))
                row.append(match.group(1))
            else:
                print(f"({file_path}): Duplicate serial number {match.group(1)} found")
                continue
        else:
            print(f"Warning({file_path}): No match found")
            continue

        for impedance in ["50", "25"]:
            keys_to_process = [
                (f"results_noise_{impedance}_all_ch_HG", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"]),
                (f"results_noise_{impedance}_all_ch_LG", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"]),
                (f"results_noise_{impedance}_sum_x3", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"]),
                (f"results_noise_{impedance}_sum_x1", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"]),
                (f"results_linearity_{impedance}_sum_x3", ["max_non_linearity", "fit_gain"]),
                (f"results_linearity_{impedance}_sum_x1", ["max_non_linearity", "fit_gain"]),
                (f"results_linearity_{impedance}_all_ch_HG", ["max_non_linearity", "fit_gain"]),
                (f"results_linearity_{impedance}_all_ch_LG", ["max_non_linearity", "fit_gain"]),
                (f"results_channel_enable_{impedance}", ["gain_crude"]),
                ("i2c_results", ["i2c_margin_list"]),
            ]
            
            i = 0;
            for key, params in keys_to_process:
                if impedance == "50" and i == 8:
                    continue
                row_data, row_flag = process_results(data, key, params, impedance)
                if i < 2:
                    gain = "lg" if i == 1 else "hg"
                    if key in data:
                        uniformity_results = data[key]
                        for ukey in uniformity_key:
                            if ukey in uniformity_results:
                                if not is_within_criteria(uniformity_results.get(ukey), gain + f"_{ukey}_{impedance}", criteria):
                                    row.append(gain + f"_{ukey}_{impedance}: {uniformity_results.get(ukey)}")
                                    flag = True
                                    param_stats[f"{gain}_{ukey}_{impedance}"]["fail"] += 1
                                else:
                                    param_stats[f"{gain}_{ukey}_{impedance}"]["pass"] += 1
                    else:
                        for ukey in uniformity_key:
                            param_stats[f"{gain}_{ukey}_{impedance}"]["fail"] += 1
                if row_data:
                    row.extend(row_data)
                if row_flag:
                    flag = True
                i = i + 1

            if f"gain_ratio_{impedance}" in data:
                gain_ratio_results = data[f"gain_ratio_{impedance}"]
                if isinstance(gain_ratio_results, list):
                    failed = False
                    for idx, value in enumerate(gain_ratio_results):
                        if idx in gain_ratio_key:
                            if not is_within_criteria(gain_ratio_results[idx], f"gain_ratio_{idx}_{impedance}", criteria):
                                row.append(f"gain_ratio_{idx}_{impedance}: {gain_ratio_results[idx]}")
                                flag = True
                                if not failed:
                                    failed = True
                                    param_stats[f"gain_ratio_{impedance}"]["fail"] += 1
                    if not failed:
                        param_stats[f"gain_ratio_{impedance}"]["pass"] += 1
                else:
                    param_stats[f"gain_ratio_{impedance}"]["fail"] += 1
            if "power_ldo" in data:
                for ldo in data["power_ldo"]:
                    ldo_name = ldo.get("name")
                    if not ldo_name:
                        continue
                    for key, value in ldo.items():
                        if key == "name":
                            continue
                        if not is_within_criteria(value, f"{ldo_name}_{key}_{impedance}", criteria):
                            row.append(f"{ldo_name}_{key}_{impedance}: {value}")
                            flag = True
                            param_stats[f"{ldo_name}_{key}_{impedance}"]["fail"] += 1
                        else:
                            param_stats[f"{ldo_name}_{key}_{impedance}"]["pass"] += 1
        # Insert Pass/Fail status at index 1
        if flag:
            row.insert(1, 'Fail' if flag else 'Pass')

            output.append(row)

        # Increment pass/fail counts
        if flag:
            fail_count += 1
        else:
            pass_count += 1

        #if pass_count + fail_count != param_stats[f"gain_ratio_{impedance}"]["pass"] + param_stats[f"gain_ratio_{impedance}"]["fail"]:
            #print(f"Warning({file_path}): Mismatch in pass/fail counts for gain_ratio_{impedance}")


    # Add a statistics row at the end of the dataframe
    stats_row = ["Overall", "", f"Passed: {pass_count}", f"Failed: {fail_count}", f"Ratio: {pass_count/(pass_count + fail_count)}"]
    output.append(stats_row)
    for param, stats in sorted(param_stats.items()):
        output.append([param, "", f'Passed: {stats["pass"]}', stats["fail"], f'Ratio: {stats["pass"]/(stats["pass"] + stats["fail"])}'])

    # Split output into main results and statistics
    main_results = output[:-1 * (len(param_stats) + 1)]
    statistics_results = output[-1 * (len(param_stats) + 1):]

    # Convert to DataFrames
    df_main = pd.DataFrame(main_results)
    df_stats = pd.DataFrame(statistics_results)

    # Save to Excel with two sheets
    with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
        df_main.to_excel(writer, sheet_name='Results', index=False)
        df_stats.to_excel(writer, sheet_name='Statistics', index=False)

if __name__ == '__main__':
    root_directory = r"C:\Users\Maxx\source\repos\alfe_histogram"
    criteria_path = r"C:\Users\Maxx\source\repos\alfe_histogram\limits.json"
    output_path = r"C:\Users\Maxx\source\repos\alfe_histogram\results.xlsx"
    file_paths = []
    filecount = 0
    for dirpath, _, filenames in os.walk(root_directory):
        if "results_all.json" in filenames:
            file_paths.append(os.path.join(dirpath, "results_all.json"))
            filecount += 1
    print(f"Found {filecount} files to process.")
    file_paths.sort(reverse=True)
    apply_cuts(file_paths, criteria_path, output_path)
