import json
import pandas as pd
import re
import os

def apply_cuts(file_paths, criteria_file_path, output_file_path):
    # Load criteria from the JSON file
    
    with open(criteria_file_path, 'r') as f:
        criteria = json.load(f)

    output = []
    pass_count = 0
    fail_count = 0

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
                        criteria_key = f"{channel}_{param}_{impedance}"
                        if not is_within_criteria(val, criteria_key, criteria):
                            row.append(criteria_key + f": {val}")
                            flag = True
        return row, flag


    for file_path in file_paths:
        row = []
        flag = False

        with open(file_path, 'r') as f:
            data = json.load(f)

        match = re.search(r'(\d{3}-\s\d{5})', file_path)
        if match:
            row.append(match.group(1))
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

            for key, params in keys_to_process:
                row_data, row_flag = process_results(data, key, params, impedance)
                if row_data:
                    row.extend(row_data)
                if row_flag:
                    flag = True

        # Insert Pass/Fail status at index 1
        row.insert(1, 'Fail' if flag else 'Pass')

        output.append(row)

        # Increment pass/fail counts
        if flag:
            fail_count += 1
        else:
            pass_count += 1


    # Add a statistics row at the end of the dataframe
    stats_row = ["Statistics", "", f"Passed: {pass_count}", f"Failed: {fail_count}", f"Ratio: {pass_count/(pass_count + fail_count)}"]
    output.append(stats_row)

    df = pd.DataFrame(output)
    df.to_csv(output_file_path, index=False)

if __name__ == '__main__':
    root_directory = "../BNL_Tray1_Tray4_Tray2_tray3_674/"
    criteria_path = "./limits.json"
    output_path = "./results.csv"
    file_paths = []
    for dirpath, _, filenames in os.walk(root_directory):
        if "results_all.json" in filenames:
            file_paths.append(os.path.join(dirpath, "results_all.json"))
    apply_cuts(file_paths, criteria_path, output_path)
