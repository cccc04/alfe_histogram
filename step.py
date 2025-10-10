import matplotlib.pyplot as plt
import numpy as np
import json
import util
import os
from sklearn.neighbors import KernelDensity

def get_step_data(x_values):
    xx = sorted(x_values)
    x_step = [0] + xx
    y_step = [0] + list(range(1, len(xx) + 1))
    return x_step, y_step

def get_values(file_paths, criteria_file_path1, criteria_file_path2):
    with open(criteria_file_path1, 'r') as f:
        criteria1 = json.load(f)
    with open(criteria_file_path2, 'r') as f:
        criteria2 = json.load(f)

    a_count = 0
    b_count = 0
    f_count = 0

    uniformity_key = {"gain_uniformity", "peaking_time_uniformity", "baseline_uniformity"}
    c_key = {"hg_lg", "sum_x1", "sum_x3"}
    u_key = ["x1", "x3"]
    gain_ratio_key = {0, 1, 2, 3}
    tc = 0
    x_f = []
    x_b = []
    for file_path in file_paths:
        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {file_path}: {e}")
                continue
        if "test_time" not in data:
            print(f"Warning: 'test_time' not found in {file_path}, skipping file")
            continue
        flag = util.get_grades(data, uniformity_key, gain_ratio_key, c_key, u_key, [criteria1, criteria2], file_path)
        
        if flag == -1:
            x_f.append(tc)
        elif flag == 0:
            x_b.append(tc)

        tc += 1

    return x_f, x_b

if __name__ == '__main__':
    # Get step data
    root_directory = "../2025-07-23/"
    spec_path = "./spec.json"
    B_limit_path = "./limits.json"
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
    file_paths = sorted(file_paths, key=util.extract_timestamp)
    x_f, x_b = get_values(file_paths, spec_path, B_limit_path)
    x_f_step, y_f_step = get_step_data(x_f)
    x_b_step, y_b_step = get_step_data(x_b)
    x_combined = np.array(sorted(x_f + x_b))
    total_events = len(x_combined)

    y_total = np.arange(1, len(x_combined) + 1)

    x_total = np.insert(x_combined, 0, 0)
    y_total = np.insert(y_total, 0, 0)

    kde = KernelDensity(kernel='gaussian', bandwidth= max(x_combined)/133).fit(x_combined[:, np.newaxis])
    x_eval = np.linspace(0, max(x_combined) - 10, 500)
    # log_density returns log(probability), so we use np.exp()
    smooth_derivative_kde = np.exp(kde.score_samples(x_eval[:, np.newaxis])) * total_events

    # Plot
    plt.figure(figsize=(12, 6))
    plt.step(x_f_step, y_f_step, where='post', label='Grade F', color='red')
    plt.step(x_b_step, y_b_step, where='post', label='Grade B', color='blue')
    plt.step(x_total, y_total, where='post', label='Total (B + F)', color='teal', linestyle='--')
 
    # Styling
    plt.xlabel('Number of Chips Tested')
    plt.ylabel('Cumulative Count')
    plt.title('Cumulative Count for Grade F and B chips')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Save the plot
    plt.savefig("step_graph_f_and_b3.png", dpi=300)
    plt.show()
    plt.close()
    
    plt.figure(figsize=(12, 6))
    #plt.plot(x_combined, y_smoothed)
    plt.plot(x_eval, smooth_derivative_kde, label='Savgol Derivative', color='orange')
    plt.xlabel('Number of Chips Tested')
    plt.ylabel('Total Cumulative Count Rate')
    plt.title('Cumulative Count Rate')
    plt.grid(True)
    plt.tight_layout()
    #plt.ylim(bottom=0)
    #plt.ylim(top=1)
    #plt.savefig("step_graph_derivative3.png", dpi=300)
    plt.show()
    plt.close()
