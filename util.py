import re
from collections import defaultdict
from datetime import datetime
import json

def extract_timestamp(file_path):
    match = re.search(r'_(\d{10})', file_path)
    return int(match.group(1)) if match else 0  # Use 0 if no timestamp found

def is_within_criteria(value, key, criteria):
    """Check if the value is within the specified criteria."""
    if key in criteria:
        min_val = criteria[key]["min"]
        max_val = criteria[key]["max"]
        return min_val <= value <= max_val
    else:
        print(f"{key} not in criteria")
    return True

def process_results(data, key_suffix, params, impedance, criterium, param_stats):
        row = []
        flag = 1
        grade = ["F", "B"]
        g = key_suffix.split("_")[-1]
        if key_suffix in data:
            results = data[key_suffix]
            channel_list = results.get("channel_list", results.get("i2c_frequency_list", None))
            if not channel_list:
                print(f"Warning: Neither 'channel_list' nor 'i2c_frequency_list' found in {key_suffix}")
                return
            i = 0
            failed = [{},{}]
            for criteria in criterium:
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

def get_grades(data, uniformity_key, gain_ratio_key, c_key, u_key, criterium, file_path, param_stats = defaultdict(lambda: {"A": 0, "B": 0, "F": 0}), row = []):
    grade = ["F", "B"]
    flag = 1
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
            row_data, row_flag = process_results(data, key, params, impedance, criterium, param_stats)
            if i < 2:
                gain = "lg" if i == 1 else "hg"
                if key in data:
                    uniformity_results = data[key]
                    for ukey in uniformity_key:
                        if ukey in uniformity_results:
                            j = 0
                            for criteria in criterium:
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
                                for criteria in criterium:
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
                        if not is_within_criteria(value, f"gain_ratio_{idx}_{impedance}", criterium[0]):
                            row.append(f"gain_ratio_{idx}_{impedance}: {value} F")
                            flag = min(flag, -1)
                            f = True
                            param_stats[f"gain_ratio_{impedance}"]["F"] += 1
                            break
                        elif not is_within_criteria(value, f"gain_ratio_{idx}_{impedance}", criterium[1]):
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
                        for criteria in criterium:
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
                for criteria in criterium:
                    if not is_within_criteria(value, f"sum_{u_key[idx]}_uniformity_{impedance}", criteria):
                        row.append(f"sum_{u_key[idx]}_uniformity_{impedance}: {value} {grade[j]}")
                        flag = j - 1 if flag > j - 1 else flag
                        param_stats[f"sum_{u_key[idx]}_uniformity_{impedance}"][grade[j]] += 1
                        break
                    j += 1
                if j == 2:
                    param_stats[f"sum_{u_key[idx]}_uniformity_{impedance}"]["A"] += 1
    return flag
