from calendar import c
import json
from socket import gaierror
import pandas as pd
import re
import os
from collections import defaultdict
from datetime import datetime
import util

def apply_cuts(file_paths, criteria_file_path1, criteria_file_path2, output_file_path, empty_paths):
    # Load criteria from the JSON file
    
    with open(criteria_file_path1, 'r') as f:
        criteria1 = json.load(f)
    with open(criteria_file_path2, 'r') as f:
        criteria2 = json.load(f)

    output = []
    a_count = 0
    b_count = 0
    f_count = 0
    param_stats = defaultdict(lambda: {"A": 0, "B": 0, "F": 0})
    grade = ["F", "B"]

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
        flag = 1
        g = key_suffix.split("_")[-1]
        if key_suffix in data:
            results = data[key_suffix]
            channel_list = results.get("channel_list", results.get("i2c_frequency_list", None))
            if not channel_list:
                print(f"Warning: Neither 'channel_list' nor 'i2c_frequency_list' found in {key_suffix}")
                return
            i = 0
            failed = [{},{}]
            for criteria in [criteria1, criteria2]:
                for idx, channel in enumerate(channel_list):
                    for param in params:
                        if param in results:
                            if param not in failed[i]:
                                failed[i][param] = False
                            value = results[param]
                            val = value[idx] if isinstance(value, list) else value
                            criteria_key = f"{channel}_{param}_{impedance}"
                            if not is_within_criteria(val, criteria_key, criteria):
                                if i == 0 or not failed[i - 1][param]:
                                    row.append(f"{criteria_key}: {val} {grade[i]}")
                                    flag = i - 1  if flag > i - 1 else flag
                                    if not failed[i][param]:
                                        failed[i][param] = True
                                        param_stats[f"{param}_{impedance}_{g}"][grade[i]] += 1
                i = i + 1
            j = -1
            for i in range(2):
                j = -1 * j
                for param, param_failed in failed[1 - i].items():
                    is_failed = param_failed if i == 0 else not param_failed
                    if not is_failed:
                        param_stats[f"{param}_{impedance}_{g}"]["A"] += j
        else:
            for param in params:
                param_stats[f"{param}_{impedance}_{g}"]["F"] += 1

        return row, flag

    uniformity_key = {"gain_uniformity", "peaking_time_uniformity", "baseline_uniformity"}
    c_key = {"hg_lg", "sum_x1", "sum_x3"}
    u_key = ["x1", "x3"]
    gain_ratio_key = {0, 1, 2, 3}
    s_n = []
    off = 0
    dup = 0

    for file_path in file_paths:
        row = []
        flag = 1

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
            cutoff_date = datetime(year=date_obj.year, month=6, day=11)

            # Check if it's later
            if date_obj < cutoff_date:
                print(f"skipping file")
                continue
        else:
            print(f"Warning: 'test_time' not found in {file_path}, skipping file")
            continue

        match = re.search(r'(\d{3}-\s\d{5})', file_path)
        if not match:
            match = re.search(r'(\d{3}-\d{5})', file_path)
        if match:
            if match.group(1) not in s_n:
                s_n.append(match.group(1))
                row.append(match.group(1))
            else:
                #print(f"({file_path}): Duplicate serial number {match.group(1)} found")
                dup += 1
                continue
        else:
            print(f"Warning({file_path}): No match found")
            continue

        ts = re.search(r'(_\d{10})', file_path)
        if not ts:
            print(f"Warning({file_path}): No timestamp found")
        else:
            row.append(ts.group(1)[1:])

        for impedance in ["25", "50"]:
            keys_to_process = [
                (f"results_noise_{impedance}_all_ch_HG", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"]),
                (f"results_noise_{impedance}_all_ch_LG", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"]),
                (f"results_noise_{impedance}_sum_x3", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"]),
                (f"results_noise_{impedance}_sum_x1", ["baseline", "noise_rms_mv", "gain", "eni", "peaking_time"]),
                (f"results_linearity_{impedance}_sum_x3", ["max_non_linearity", "fit_gain"]),
                (f"results_linearity_{impedance}_sum_x1", ["max_non_linearity", "fit_gain", "peaking_time_std"]),
                (f"results_linearity_{impedance}_all_ch_HG", ["max_non_linearity", "fit_gain"]),
                (f"results_linearity_{impedance}_all_ch_LG", ["max_non_linearity", "fit_gain"]),
                (f"results_channel_enable_{impedance}", ["gain_crude"]),
                (f"results_baseline_{impedance}", ["residual", "slope_fit", "offset"]),
                ("i2c_results", ["i2c_margin_list", "i2c_phase_list"]),
            ]
            
            i = 0;
            for key, params in keys_to_process:
                if impedance == "50" and i > 7:
                    continue
                row_data, row_flag = process_results(data, key, params, impedance)
                if i < 2:
                    gain = "lg" if i == 1 else "hg"
                    if key in data:
                        uniformity_results = data[key]
                        for ukey in uniformity_key:
                            if ukey in uniformity_results:
                                j = 0
                                for criteria in [criteria1, criteria2]:
                                    if not is_within_criteria(uniformity_results[ukey], gain + f"_{ukey}_{impedance}", criteria):
                                        row.append(gain + f"_{ukey}_{impedance}: {uniformity_results[ukey]} {grade[j]}")
                                        flag = j - 1 if flag > j - 1 else flag
                                        param_stats[f"{gain}_{ukey}_{impedance}"][grade[j]] += 1
                                        break
                                    j += 1
                                if j == 2:
                                    param_stats[f"{gain}_{ukey}_{impedance}"]["A"] += 1
                    else:
                        for ukey in uniformity_key:
                            param_stats[f"{gain}_{ukey}_{impedance}"]["F"] += 1
                if i == 9 and impedance == "25":
                    if key in data:
                        baseline_results = data[key]
                        if "dclvl_sh_calib" in baseline_results:
                            c_results = baseline_results["dclvl_sh_calib"]
                            for ckey in c_key:
                                if ckey in c_results:
                                    j = 0
                                    for criteria in [criteria1, criteria2]:
                                        if not is_within_criteria(c_results[ckey], f"dclvl_sh_calib_{ckey}", criteria):
                                            row.append(f"dclvl_sh_calib_{ckey}: {c_results[ckey]} {grade[j]}")
                                            flag = j - 1 if flag > j - 1 else flag
                                            param_stats[f"dclvl_sh_calib_{ckey}"][grade[j]] += 1
                                            break
                                        j += 1
                                    if j == 2:
                                        param_stats[f"dclvl_sh_calib_{ckey}"]["A"] += 1

                if row_data:
                    row.extend(row_data)
                if flag > row_flag:
                    flag = row_flag
                i = i + 1
            if f"gain_ratio_{impedance}" in data:
                gain_ratio_results = data[f"gain_ratio_{impedance}"]
                if isinstance(gain_ratio_results, list):
                    f = False
                    b = False
                    for idx, value in enumerate(gain_ratio_results):
                        if idx in gain_ratio_key:
                            if not is_within_criteria(value, f"gain_ratio_{idx}_{impedance}", criteria1):
                                row.append(f"gain_ratio_{idx}_{impedance}: {value} F")
                                flag = min(flag, -1)
                                f = True
                                param_stats[f"gain_ratio_{impedance}"]["F"] += 1
                                break
                            elif not is_within_criteria(value, f"gain_ratio_{idx}_{impedance}", criteria2):
                                row.append(f"gain_ratio_{idx}_{impedance}: {value} B")
                                flag = min(flag, 0)
                                b = True
                        else:
                            print(f"Warning({file_path}): gain_ratio_{impedance} index {idx} not in gain_ratio_key")

                    if not f and b:
                        param_stats[f"gain_ratio_{impedance}"]["B"] += 1
                    elif not f and not b:
                        param_stats[f"gain_ratio_{impedance}"]["A"] += 1
                else:
                    print(f"Warning({file_path}): gain_ratio_{impedance} is not a list")
            else:
                param_stats[f"gain_ratio_{impedance}"]["F"] += 1

            if  impedance == "25":
                if "power_ldo" in data:
                    for ldo in data["power_ldo"]:
                        ldo_name = ldo.get("name")
                        if not ldo_name:
                            continue
                        for key, value in ldo.items():
                            if key == "name":
                                continue
                            j = 0
                            for criteria in [criteria1, criteria2]:
                                if not is_within_criteria(value, f"{ldo_name}_{key}_{impedance}", criteria):
                                    row.append(f"{ldo_name}_{key}_{impedance}: {value} {grade[j]}")
                                    flag = j - 1 if flag > j - 1 else flag
                                    param_stats[f"{ldo_name}_{key}_{impedance}"][grade[j]] += 1
                                    break
                                j += 1
                            if j == 2:
                                param_stats[f"{ldo_name}_{key}_{impedance}"]["A"] += 1
                else:
                    param_stats[f"{ldo_name}_{key}_{impedance}"]["F"] += 1
                    print(f"Warning({file_path}): power_ldo not found in data")

            if f"results_sum_uniformity_{impedance}" in data:
                uniformity_results = data[f"results_sum_uniformity_{impedance}"]
                uniformity_results = uniformity_results[f"uniformity"]
                for idx, value in enumerate(uniformity_results):
                    j = 0
                    for criteria in [criteria1, criteria2]:
                        if not is_within_criteria(value, f"sum_{u_key[idx]}_uniformity_{impedance}", criteria):
                            row.append(f"sum_{u_key[idx]}_uniformity_{impedance}: {value} {grade[j]}")
                            flag = j - 1 if flag > j - 1 else flag
                            param_stats[f"sum_{u_key[idx]}_uniformity_{impedance}"][grade[j]] += 1
                            break
                        j += 1
                    if j == 2:
                        param_stats[f"sum_{u_key[idx]}_uniformity_{impedance}"]["A"] += 1
                

        # Insert Pass/Fail status at index 1

        if flag == -1:
            row.insert(1, 'F')
            output.append(row)
            f_count += 1
        elif flag == 0:
            row.insert(1, 'B')
            output.append(row)
            b_count += 1
        else:
            row.insert(1, 'A')
            a_count += 1

    empty_count = 0
    for file_path in empty_paths:
        row = []

        match = re.search(r'(\d{3}-\s\d{5})', file_path)
        if not match:
            match = re.search(r'(\d{3}-\d{5})', file_path)
        if match:
            if match.group(1) not in s_n:
                s_n.append(match.group(1))
                row.append(match.group(1))
            else:
                print(f"({file_path}): Duplicate serial number {match.group(1)} found")
                dup += 1
                continue
        else:
            print(f"Warning({file_path}): No match found")
            continue
        row.extend("F")
        output.append(row)
        f_count += 1
        empty_count += 1
    # Add a statistics row at the end of the dataframe
    stats_row = ["Overall", a_count, b_count, f_count, a_count/(a_count + b_count + f_count)]
    output.append(stats_row)
    for param, stats in sorted(param_stats.items()):
        output.append([param, stats["A"], stats["B"], stats["F"] + empty_count, stats["A"]/(stats["A"] + stats["B"] + stats["F"] + empty_count)])

    # Split output into main results and statistics
    main_results = output[:-1 * (len(param_stats) + 1)]
    statistics_results = output[-1 * (len(param_stats) + 1):]
    statistics_results.insert(0,["", f"A", f"B", f"F", f"Ratio"])

    # Convert to DataFrames
    df_main = pd.DataFrame(main_results)
    df_stats = pd.DataFrame(statistics_results)

    # Save to Excel with two sheets
    with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
        df_main.to_excel(writer, sheet_name='Results', index=False)
        df_stats.to_excel(writer, sheet_name='Statistics', index=False, header=False)
        # Get workbook and worksheet objects
        workbook  = writer.book
        worksheet = writer.sheets['Statistics']
        percent_format = workbook.add_format({'num_format': '0.00%'})

        # Apply percentage format to the last column of df_stats
        percent_col_idx = len(df_stats.columns) - 1
        worksheet.set_column(percent_col_idx, percent_col_idx, 12, percent_format)

if __name__ == '__main__':
    root_directory = "../july/"
    spec_path = "./spec.json"
    B_limit_path = "./limits.json"
    output_path = "./results9.xlsx"
    file_paths = []
    empty_paths = []
    filecount = 0
    for dirpath, _, filenames in os.walk(root_directory):
        if "results_all.json" in filenames:
            file_paths.append(os.path.join(dirpath, "results_all.json"))
            filecount += 1
        elif "metadata.json" in filenames:
            empty_paths.append(dirpath)
            filecount += 1
        else:
            print(f"Warning: No results_all.json or metadata.json found in {dirpath}")
    print(f"Found {filecount} files to process.")
    file_paths = sorted(file_paths, key=util.extract_timestamp, reverse=True)
    apply_cuts(file_paths, spec_path, B_limit_path, output_path, empty_paths)
