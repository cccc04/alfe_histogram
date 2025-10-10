import json
import re
from collections import defaultdict
from datetime import datetime
import os
import pandas as pd
import os
import util

def save_exel(file_paths, criteria_file_path1, criteria_file_path2, output_file_path, empty_paths):
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

    uniformity_key = {"gain_uniformity", "peaking_time_uniformity", "baseline_uniformity"}
    c_key = {"hg_lg", "sum_x1", "sum_x3"}
    u_key = ["x1", "x3"]
    gain_ratio_key = {0, 1, 2, 3}
    s_n = []
    off = 0
    dup = 0

    for file_path in file_paths:
        row = []

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
            cutoff_date = datetime(year=date_obj.year, month=1, day=11)

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
                row.append(match.group(1))
            else:
                print(f"({file_path}): Duplicate serial number {match.group(1)} found")
                dup += 1
                continue
        else:
            match = re.search(r'(\d{8})', file_path)
            if not match:
                match = re.search(r'(\d{6})', file_path)
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

        ts = re.search(r'(_\d{10})', file_path)
        if not ts:
            print(f"Warning({file_path}): No timestamp found")
        else:
            row.append(ts.group(1)[1:])

        flag = util.get_grades(data, uniformity_key, gain_ratio_key, c_key, u_key, [criteria1, criteria2], file_path, param_stats, row)

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

        match = re.search(r'(\d{3}-\d{5})', file_path)
        if not match:
            match = re.search(r'(\d{3}-\s\d{5})', file_path)  # Handle cases with space
        if match:
            if match.group(1) not in s_n:
                s_n.append(match.group(1))
                row.append(match.group(1))
            else:
                print(f"({file_path}): Duplicate serial number {match.group(1)} found")
                dup += 1
                continue
        else:
            match = re.search(r'(\d{8})', file_path)
            if not match:
                match = re.search(r'(\d{6})', file_path)
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
    root_directory = "../2025-08/"
    spec_path = "./spec.json"
    B_limit_path = "./limits.json"
    output_path = "./resultsijctst.xlsx"
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
    save_exel(file_paths, spec_path, B_limit_path, output_path, empty_paths)
