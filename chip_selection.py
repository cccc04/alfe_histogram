from calendar import c
import json
from socket import gaierror
import pandas as pd
import re
import os
import shutil
from collections import defaultdict
from datetime import datetime, timezone, timedelta

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
    gain_ratio_key = {0, 1, 2, 3}
    s_n = []
    dup = 0
    t_out = 0
    prt = False
    processed = 0
           
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
        row = []
        flag = 1

        with open(file_path, 'r') as f:
            data = json.load(f)
        
        stamp = int(re.search(r'(\d{10})', file_path).group(1))
        dt = datetime.fromtimestamp(stamp, tz=timezone(timedelta(hours=-4)))  # or use fromtimestamp() for local time

        '''
        if (dt > vece[2] or dt < vecs[2]):
            continue
        
        elif prt == False:
            print(f"Processing file: {file_path} at {dt}")
            prt = True
        '''
        
        processed += 1
        
        
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

        if out:
            #print(f"Timestamp is outside the range: {match.group(1)} / {dt}")
            t_out += 1
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



        for impedance in ["25", "50"]:
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

        stamp = int(re.search(r'(\d{10})', file_path).group(1))
        dt = datetime.fromtimestamp(stamp, tz=timezone(timedelta(hours=-4)))  # or use fromtimestamp() for local time

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
    stats_row = ["Overall", "", f"A: {a_count}", f"B: {b_count}", f"F: {f_count}", f"Ratio: {a_count/(a_count + b_count + f_count)}"]
    output.append(stats_row)
    for param, stats in sorted(param_stats.items()):
        output.append([param, "", stats["A"], stats["B"], stats["F"] + empty_count, f'Ratio: {stats["A"]/(stats["A"] + stats["B"] + stats["F"] + empty_count)}'])

    # Split output into main results and statistics
    main_results = output[:-1 * (len(param_stats) + 1)]
    statistics_results = output[-1 * (len(param_stats) + 1):]

    print(f"Duplicate serial numbers found: {dup}")
    print(f"Timestamp out of range: {t_out}")
    print(f"Processed {processed} files.")

    # Convert to DataFrames
    df_main = pd.DataFrame(main_results)
    df_stats = pd.DataFrame(statistics_results)

    # Save to Excel with two sheets
    with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
        df_main.to_excel(writer, sheet_name='Results', index=False)
        df_stats.to_excel(writer, sheet_name='Statistics', index=False)

if __name__ == '__main__':
    root_directory = "../all/"
    spec_path = "./spec.json"
    B_limit_path = "./limits.json"
    output_path = "./results.xlsx"
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
    file_paths.sort(reverse=True)
    apply_cuts(file_paths, spec_path, B_limit_path, output_path, empty_paths)
