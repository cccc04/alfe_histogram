from asyncio.windows_events import NULL
from calendar import c
from math import e
import pickle
import string
import numpy as np
import matplotlib
matplotlib.use('qtagg')
import matplotlib.pyplot as plt
import os
import pandas as pd
import json
import re

# used when a line is clicked in interactive mode to store for after the update loop
clickedIDpath = set()

# lookup table for raw data waveform to a test
def returnTest(key):
    match key:
        case "data_channel_enable_25":
            return ("None")
        case "data_peaking_time_25":
            return ("hg_peaking_time_uniformity_25","lg_peaking_time_uniformity_25","HG_peaking_time_25","LG_peaking_time_25","x1_peaking_time_25","x3_peaking_time_25")
        case "data_noise_25_all_ch_HG_signal":
            return ("HG_eni_25","HG_noise_rms_mv_25")
        case "data_linearity_25_all_ch_HG":
            return ("HG_max_non_linearity_25")
        case "data_noise_25_all_ch_LG_signal":
            return ("LG_eni_25","LG_noise_rms_mv_25")
        case "data_linearity_25_all_ch_LG":
            return ("LG_max_non_linearity_25")
        case "data_noise_25_sum_x1_signal":
            return ("x1_eni_25","x1_noise_rms_mv_25")
        case "data_linearity_25_sum_x1":
            return ("x1_max_non_linearity_25")
        case "data_noise_25_sum_x3_signal":
            return ("x3_eni_25","x3_noise_rms_mv_25")
        case "data_linearity_25_sum_x3":
            return ("x3_max_non_linearity_25_x3")
        case "data_sum_uniformity_25_signal":
            return ("hg_baseline_uniformity_25", "hg_gain_uniformity_25")
        case "data_peaking_time_50":
            return ("hg_peaking_time_uniformity_50","lg_peaking_time_uniformity_50","hg_peaking_time_50","lg_peaking_time_50","x1_peaking_time_50","x3_peaking_time_50")
        case "data_noise_50_all_ch_HG_signal":
            return ("HG_eni_50","HG_noise_rms_mv_50")
        case "data_linearity_50_all_ch_HG":
            return ("HG_max_non_linearity_50")
        case "data_noise_50_all_ch_LG_signal":
            return ("LG_eni_50","LG_noise_rms_mv_50")
        case "LG_data_linearity_50_all_ch":
            return ("max_non_linearity_50_LG")
        case "data_noise_50_sum_x1_signal":
            return ("x1_eni_50","x1_noise_rms_mv_50")
        case "data_linearity_50_sum_x1":
            return ("x1_max_non_linearity_50")
        case "data_noise_50_sum_x3_signal":
            return ("x3_eni_50","x3_noise_rms_mv_50")
        case "data_linearity_50_sum_x3":
            return ("x3_max_non_linearity_50")
        case "data_sum_uniformity_50_signal":
            return ("hg_baseline_uniformity_50","hg_gain_uniformity_50")
        case _:
            return ("None",)

    

# read json file from plot histograms
def read_json_files(file_paths, impedance):
    # Define per-channel parameters (excluding uniformity)
    channel_params = [
        "baseline", "noise_rms_mv", "gain", "eni", 
        "peaking_time", "max_non_linearity", "fit_gain", 
        "gain_crude", "i2c_margin_list"
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
        if os.path.getsize(file_path) == 0:
            print(f"Skipping empty file: {file_path}")
            continue

        try:
            with open(file_path, 'r') as f:
                print(file_path)
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON: {file_path}")
            continue

        match = re.search(r'(\d{5,9})', file_path)

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
        process_results(data, "i2c_results", ["i2c_margin_list"])

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
       



def dim(a):
    if not type(a) == list:
        return []
    return [len(a)] + dim(a[0])

def plot_waveform(dataset_name, file_paths, output_directory, excelSheetGrades, chipGradeSelect, idToCheck,channelSelect,deviationSelect):
    
    
    for channel in range(4):
        all_waveforms = []   # Collect waveforms per channel
        all_labels = []      # Collect matching labels (or IDs)
        all_filepaths = []   # Optional: if you want to store paths
        xAvgwaveform = []
        try:
        # make sure input is an int and set it to it if not a string (All)
            if type(int(channelSelect)) == int:
                channel = int(channelSelect)
            print(f"ChannelSelect: {channelSelect}")
            print(f"channel: {channel}")
            print(f"channel type {type(int(channelSelect))}")
        except:
            #raises value error if input is a string
            pass

        plt.figure(figsize=(12, 6))  # One figure
        plt.gcf().canvas.mpl_connect('pick_event', onpick)


        for file_path in file_paths:
            try:
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                    
            except (EOFError, pickle.UnpicklingError) as e:
                print(f"Skipping file due to error: {file_path} - {e}")
                
                continue

                #print(file_path)
            # Inspect 3D datasets
            #for key in data.keys():
                # array = np.array(data[key])
                 #if array.ndim == 30:
                   #print(f"3D Dataset Found: {key}")
                  # print(f"Shape: {array.shape}")
                   #print("First 10 samples from [0, 0, :]:")
                   #print(array[0, 0, :10])
                   #break

        
            if dataset_name not in data:
                print(f"Dataset '{dataset_name}' not found in {file_path}. Available datasets are:")
                for key in data.keys():

                    print(f"  - {key}")
                continue  # Skip this file and continue
            print(dataset_name)
            print(dim(data[dataset_name]))
            ID = (int(file_path.translate({ord(i): None for i in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ:  \  _ . \n'})))
            
            print(idToCheck)
            
            if idToCheck != "None":
                ids = [idToCheck] if isinstance(idToCheck, str) else idToCheck
                if str(ID) not in [str(id_) for id_ in ids]:
                    print(ID)
                    print("Wrong Id")
                    continue


            grade, excelSheetGrades = getGrade(excelSheetGrades,ID, dataset_name )
            print("grading")
            if grade == "A":
                if "A" not in chipGradeSelect and "All" not in chipGradeSelect:
                    print("A grading")
                    continue
                colorGrade = "Green"

            elif grade == "B":
                if "B" not in chipGradeSelect and "All" not in chipGradeSelect:
                    print("B grading")
                    continue
                colorGrade = "Orange"

            elif grade == "F":
                if "F" not in chipGradeSelect and "All" not in chipGradeSelect:
                    continue
                colorGrade = "Red"

            else:
                if "All" not in chipGradeSelect:
                    print("all grading")
                    continue
                print(ID)
                colorGrade = "Blue"

            #print(grade)
            
            try:
                #due to weird data linearity matrix
                dataset = np.array(data[dataset_name])
                #print(f"{dataset_name} shape: {dataset.shape}, dtype: {dataset.dtype}")
            except ValueError as e:
               # print("Error converting to NumPy array:", e)
                # Try manual stacking
                
                try:
                    dataset = np.stack(data[dataset_name])
                    #print("Used np.stack instead")
                except:
                    #if its the weird linearity data 
                    #For channel c in a dataset
                    c = 1
                    for c in range(4):
                        try:
                            measured = data[dataset_name][2][c]
                           # expected = data[dataset_name][3][c]
                            x_axis = data[dataset_name][4]
                        except: 
                           # print("incomplete dataset")
                           #print("\n")
                            pass
                            
                    if deviationSelect != "Yes":
                        line, = plt.plot(x_axis, measured, color = colorGrade, label='Measured', linewidth = .6, picker = True, pickradius = 1)
                        # store file path of line 
                        line.customID = file_path
                    else: 
                        print(f"xaxis: {x_axis}")
                        print(f"channel: {channel}")
                        xAvgwaveform = x_axis
                        avg_waveform = measured
                        all_waveforms.append(avg_waveform)
                        all_labels.append(os.path.basename(file_path))
                        all_filepaths.append(file_path)


                    
                    plt.xlabel("Input Level")
                    plt.ylabel("Output Response")
                    plt.title(f"Linearity Plot - Channel {c}")
                   # plt.legend()
                    plt.grid(True)
                    #plt.show()
                    continue
                 
                raw_dataset = data[dataset_name]

                for i, item in enumerate(raw_dataset):
                    try:
                        shape = np.shape(item)
                       # print(f"Element {i}: shape = {shape}")
                    except Exception as e:
                        print(f"Element {i}: Error determining shape - {e}")
                
                


                print(dim(data[dataset_name]))
               # print((data[dataset_name]))
                
                

            # === 1D ===
            if dataset.ndim == 1:
                if deviationSelect != "Yes":
                    line, = plt.plot(dataset, color = colorGrade, label=f'{os.path.basename(file_path)}', linewidth = .6, picker = True, pickradius = 1)
                    line.customID = file_path
                else: 
                    avg_waveform = np.mean(dataset[:, channel, :], axis=0)
                    all_waveforms.append(avg_waveform)
                    all_labels.append(os.path.basename(file_path))
                    all_filepaths.append(file_path)
            # === 2D ===
            elif dataset.ndim == 2:
                for i, channelData in enumerate(dataset):
                    if deviationSelect != "Yes":
                        line, = plt.plot(channelData, color = colorGrade, label=f'{os.path.basename(file_path)} - Ch {i}', linewidth = .6, picker = True, pickradius = 1)
                        line.customID = file_path
                    else:
                        #print(dataset)
                        #print("channeldata")
                        print(channelData)
                        
                        avg_waveform = channelData
                        print(avg_waveform)
                        all_waveforms.append(avg_waveform)
                        all_labels.append(os.path.basename(file_path))
                        all_filepaths.append(file_path)
            # === 3D ===
            elif dataset.ndim == 3:
                
    
                     # Average over blocks for this channel
                 avg_waveform = np.mean(dataset[:, channel, :], axis=0)
                 #print(f"Average waveform: {avg_waveform}")
                 if deviationSelect != "Yes":
                     label = f'{os.path.basename(file_path)} - Ch {channel}'
                     line, = plt.plot(avg_waveform, color = colorGrade, label=label, linewidth = .8, picker = True, pickradius = 1)
                     line.customID = file_path
                 else: 
                     avg_waveform = np.mean(dataset[:, channel, :], axis=0)
                     print(f"average waveform: {avg_waveform}")
                     all_waveforms.append(avg_waveform)
                     all_labels.append(os.path.basename(file_path))
                     all_filepaths.append(file_path)


            else:
                print(f"Unsupported data dimensions: {dataset.ndim}D")
                continue
            
            
            if str(ID) == str(idToCheck):
                        print(ID)
                        
                        break

        plt.xlabel("Sample Index")
        plt.ylabel("Amplitude")
        plt.grid(True)
        plt.title(f"Waveform: {dataset_name}, Channel: {channel}")
        #plt.legend(fontsize='small', ncol=2)
    
        # Save and show
        #print(type(channel))
        if type(channel) != "int":
            channel = "All"
        filename = f"{dataset_name}_{channel}_graph.png"
       # print(filename)
       # print(channel)

        if all_waveforms and deviationSelect == "Yes":
            all_waveforms_np = np.array(all_waveforms)  # Shape: (num_waveforms, num_samples)
            mean_wave = np.mean(all_waveforms_np, axis=0)

            # Calculate Euclidean distance from mean for each waveform
            distances = np.linalg.norm(all_waveforms_np - mean_wave, axis=1)

            # 2x the mean
            threshold = np.mean(distances) + 2 * np.std(distances)

            #test if a variable that stores x data is there, if not defulat to an enumerate
            if xAvgwaveform:
                for idx, (wave, dist) in enumerate(zip(all_waveforms_np, distances)):
                    color = 'red' if dist > threshold else 'blue'
                    label = all_labels[idx]
                    line, = plt.plot( xAvgwaveform, wave, color=color, label=label, linewidth=0.8, picker=True, pickradius=1)
                    line.customID = all_filepaths[idx]
            else:

                for idx, (wave, dist) in enumerate(zip(all_waveforms_np, distances)):
                    color = 'red' if dist > threshold else 'blue'
                    label = all_labels[idx]
                    line, = plt.plot(wave, color=color, label=label, linewidth=0.8, picker=True, pickradius=1)
                    line.customID = all_filepaths[idx]



        plt.savefig(os.path.join(output_directory, filename), dpi=300)
        
     
        plt.show()
        displayInformation()




        plt.close()
        # break the loop if a channel is selected
        if channelSelect != "All":
            break
            


def displayInformation():
    #could have also used a dict instead of a tuple    
        options = (
        "1V2",
        "2V5",
        "baseline",
        "eni",
        "fit_gain",
        "gain",
        "gain_crude",
        "gain_ratio",
        "hg_baseline_uniformity",
        "hg_gain_uniformity",
        "hg_peaking_time_uniformity",
        "i2c_margin_list_25_results",
        "lg_baseline_uniformity",
        "lg_gain_uniformity",
        "lg_peaking_time_uniformity",
        "max_non_linearity",
        "noise_rms_mv",
        "peaking_time_25",
        "pwr_total_mw_power"
        )    
        
        loadjsonZip = (
        "power_ldo_values",
        "power_ldo_values",
        "Channel Values",
        "Channel Values",
        "Channel Values",
        "Channel Values",
        "Channel Values",
        "gain_ratio_values",
        "uniformity_hg",
        "uniformity_hg",
        "uniformity_hg",
        "Channel Values",
        "uniformity_lg",
        "uniformity_lg",
        "uniformity_lg",
        "Channel Values",
        "Channel Values",
        "Channel Values",
        "power_ldo_values"
            
            )
        
        
        IDarray = []
        minSpecArray = []
        maxSpecArray = []
        minWarnArray = []
        maxWarnArray = []
        valuesArray = []
        pathInfo = ""
        outerkeySelection= ""
        keySelection = ""
        outerKeysSelect = ""
        impedenceSelect = ""


        


        file_paths2 = []
        IDspath = clickedIDpath
        #try:
        #iterate through all IDs clicked
        for IDspaths in IDspath:
            
            
            #print(IDspath)
            # Collect  results_all.json file paths.
            motherdir = os.path.dirname(IDspaths)
            #print(motherdir)
            for dirpath, _, filenames in os.walk(motherdir):
                if "results_all.json" in filenames:
                    file_paths2.append(os.path.join(dirpath, "results_all.json"))

            loadedJson = {"",""}
            #print(file_paths2)
            #print("we here")
            ID = (int(IDspaths.translate({ord(i): None for i in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ:  \  _ . \n'})))
            IDarray.append(ID)
            #print("now we here")
            
            while loadedJson == {"",""}:
                if pathInfo == "":
                    pathInfo = input(f"Would you like to display information about {ID}? Y/N")
            
                if pathInfo == "Y":
                   if outerKeysSelect == "" and impedenceSelect == "":
                        outerKeysSelect = input(f"Please select one of the following to display, or All {options}")
                        impedenceSelect = input("Please enter 50 or 25 for impedence")
                   #print(file_paths2)
                   

                    #for getting limits
                   
                   xlim_limits = load_existing_xlim(root_directory, impedenceSelect)
                   xlim_limits2 = load_existing_xlim2(root_directory,impedenceSelect)
                        


                   channel_values, power_ldo_values, uniformity_hg, uniformity_lg, gain_ratio_values = read_json_files(file_paths2, impedenceSelect)
                  # print("its working")
           
                   loadedJson = {"",""}
                   key_prefix = ""
                    #get corresponding key to load
                   zippedVar = zip(options, loadjsonZip)
               
                   for jsonOptions, jsonKey in zippedVar:
                   # use user input to select a loaded json tree
                       if jsonOptions == outerKeysSelect:
                           
                           match jsonKey:
                               case "power_ldo_values":
                                   loadedJson = power_ldo_values
                                   key_prefix = "power_ldo"
                                   break
                               case "Channel Values":
                                   loadedJson = channel_values
                                   key_prefix = "channel"
                                   break
                               case "gain_ratio_values":
                                   loadedJson = gain_ratio_values
                                   key_prefix = "gain_ratio"
                                   break
                               case "uniformity_hg":
                                   loadedJson = uniformity_hg
                                   key_prefix = "hg"
                                   break
                               case "uniformity_lg":
                                   loadedJson = uniformity_lg
                                   key_prefix = "lg"
                                   break
                               case _:
                                   print("json key not found")
                                   
                   
                    # probally not necessary
                   if loadedJson != {"",""}:
                       break
                else:
                    break
            outerKeys = set()
            paramKeys = set()                 
            #print(loadedJson)          
            try: 
                for outer_key, inner_dict in loadedJson.items():
                     #print(f"outer key: {outer_key}")
                     #print(f"innder_dict: {inner_dict}")
                     if not isinstance(inner_dict, dict):
                        inner_dict = {outer_key: inner_dict}
                        outer_key = None
                     for param, values in inner_dict.items():
                        # print(f"inner dict: {inner_dict}")
                         #print(f"param: {param}")
                         #print(f"outer key: {outer_key}")
                        # paramKeys.add(param)
                        # outerKeys.add(outer_key)
                         if values:
                            #print(f"values: {values}")
                            paramKeys.add(param)
                            outerKeys.add(outer_key)
                            #print("\n")
            except: 
                print("items not found")
            if outerkeySelection == "":
                if outer_key == None:
                    outerkeySelection = None
                else:
                    outerkeySelection = input(f"Please select one of the following O: {outerKeys}")
                
            keysForParam = set()
            # remove param keys whose value is None
            for outer_key, inner_dict in loadedJson.items():
                         #print(f"outer key: {outer_key}")
                         #print(f"innder_dict: {inner_dict}")
                         if not isinstance(inner_dict, dict):
                            inner_dict = {outer_key: inner_dict}
                            outer_key = None
                         for param, values in inner_dict.items():
                             #print(f"param: {param}")
                             #print(f"values: {values}")   
                            # print(f"outer_key: {outer_key}")
                             #print(f"outer_key selection {outerkeySelection}")
                            # print(f"param: {param}")
                             #print(f"values: {values}")
                             if values and outer_key == outerkeySelection:
                                 keysForParam.add(param)
                                 
                                 
                # only input for first go
            if keySelection == "":
              keySelection = input(f"Please select one of the following P: {keysForParam}")
            
            if keySelection not in keysForParam:
                print("Input not in list, defaulting to displaying all")
                for outer_key, inner_dict in loadedJson.items():
                         #print(f"outer key: {outer_key}")
                         #print(f"innder_dict: {inner_dict}")
                         if not isinstance(inner_dict, dict):
                            inner_dict = {outer_key: inner_dict}
                            outer_key = None
                         for param, values in inner_dict.items():
                             #print(f"param: {param}")
                            # print(f"values: {values}")
                             if values:
                                #print(f"{param}: {values}")
                                                                # use try incase no channel value, then values not an array 
                                valuesArray = values
                                

                                full_key = f"{key_prefix}_{param}_{impedenceSelect}" if outer_key is None else f"{outer_key}_{param}_{impedenceSelect}"
                                xlim = xlim_limits[full_key]
                                xlim2 = xlim_limits2[full_key]
                               # print(f"B grade Min: {xlim["min"]}")
                               # print(f"B grade Max: {xlim["max"]}")
                               # print(f"Spec Min: {xlim2["min"]}")
                               # print(f"Spec Max: {xlim2["max"]}")
                                minWarnArray.append(xlim["min"])
                                maxWarnArray.append(xlim["max"])
                                minSpecArray.append(xlim2["min"])
                                maxSpecArray.append(xlim2["max"])
                                #print("\n")
            
            else:
                for outer_key, inner_dict in loadedJson.items():
                         #print(f"outer key: {outer_key}")
                         #print(f"innder_dict: {inner_dict}")
                         
                         if not isinstance(inner_dict, dict):
                            inner_dict = {outer_key: inner_dict}
                            outer_key = None
                         for param, values in inner_dict.items():
                             #print(f"outer_key: {outer_key}")
                            # print(f"param: {param}")
                            # print(f"values: {values}")
                            # print(f"keyselection: {keySelection}")
                            # print(f"outerkey: {outer_key}")
                            # print(f"outerkeyselection: {outerkeySelection}")
                             if values and param == keySelection and outer_key == outerkeySelection:
                                #print(f"{param}: {values}")
                                #print(f"Values Oj:{values}")
                                valuesArray = values
                                


                                full_key = f"{key_prefix}_{param}_{impedenceSelect}" if outer_key is None else f"{outer_key}_{param}_{impedenceSelect}"
                                xlim = xlim_limits[full_key]
                                xlim2 = xlim_limits2[full_key]
                                #print(f"B grade Min: {xlim["min"]}")
                                #print(f"B grade Max: {xlim["max"]}")
                                #print(f"Spec Min: {xlim2["min"]}")
                                #print(f"Spec Max: {xlim2["max"]}")
                                minWarnArray.append(xlim["min"])
                                maxWarnArray.append(xlim["max"])
                                minSpecArray.append(xlim2["min"])
                                maxSpecArray.append(xlim2["max"])
                                #print("\n")




        #print(f"IDs: {IDarray}")
        #print(f"B grade Min: {minWarnArray}")
        #print(f"B grade Max: {maxWarnArray}")
        #print(f"Spec Min: {minSpecArray}")
        #print(f"Spec Max: {maxSpecArray}")

        
        print(f"{'ID':<10} {'Value':<10} {'B Min':<10} {'B Max':<10} {'Spec Min':<10} {'Spec Max':<10}")
        for ID, val, bmin, bmax, smin, smax in zip(IDarray, valuesArray, minWarnArray, maxWarnArray, minSpecArray, maxSpecArray):
            print(f"{ID:<10} {val:<10} {bmin:<10} {bmax:<10} {smin:<10} {smax:<10}")








        input("press anything to continue")
       # except:
            
            #print("Path not found 34")
            

# parameter name
#filename = f"{label.lower()}_{param}_{impedance}_histogram.png" if outer_key is None \
 #                   else f"{outer_key}_{param}_{impedance}_histogram.png"
        

#get the excel sheet to a simple matrix, one column with id, other chip grade, sorted so faster search
def getGrade(gradeExcel, ID, name):
    

    # Load the Excel file if needed
    if not isinstance(gradeExcel, pd.DataFrame):
        df = pd.read_excel(gradeExcel)
        print("This should run once")
        # Sort by the first column (ID)
        gradeExcel = df.iloc[df.iloc[:, 0].argsort()]
    
    # Convert to NumPy array
    gradeExcelarr = gradeExcel.to_numpy()

    # Convert both ID and Excel column to string for safe comparison
    id_str = str(ID)
    id_column = gradeExcelarr[:, 0].astype(str)

    # Binary search for the ID
    idx = np.searchsorted(id_column, id_str)

    # Check bounds and confirm exact match
    if idx >= len(gradeExcelarr) or id_column[idx] != id_str:
        print(f"ID {ID} not found.")
        return "A", gradeExcel

    # Default grade
    grade = "A"
    testKeys = returnTest(name)
   # print(f"[DEBUG] testKeys: {testKeys} (type: {type(testKeys)})")

    # Force testKeys to be a tuple
    if isinstance(testKeys, str):
        testKeys = (testKeys,)

    # If no special tests apply, just use the default grade
    if testKeys == ("None",):
        grade = gradeExcelarr[idx, 1]
    else:
        print(testKeys)
        print("testkeys\n")

        for testKey in testKeys:
            #print("testKey\n")
            #print(testKey)

            for i in range(2, gradeExcelarr.shape[1]):  # Start at column 2
                dataString = gradeExcelarr[idx, i]

                if dataString != dataString:  # NaN check
                    #print("nan ran")
                    break

                elif testKey.lower() in str(dataString).lower():
                   # print("grade made\n")
                    grade = str(dataString)[-1]  # Last character is the grade
                    if grade == "F":
                        break

    print(grade)
    return grade, gradeExcel


def load_existing_xlim(output_directory, impedance):
    xlim_file_path = os.path.join(output_directory, f"limits.json")
    if os.path.exists(xlim_file_path):
        with open(xlim_file_path, "r") as f:
            return json.load(f)  # Load existing xlim limits
    return {}  # Return an empty dictionary if no existing file is found    



def load_existing_xlim2(output_directory, impedance):
    xlim_file_path = os.path.join(output_directory, f"spec.json")
    if os.path.exists(xlim_file_path):
        with open(xlim_file_path, "r") as f:
            return json.load(f)  # Load existing xlim limits
    return {}  # Return an empty dictionary if no existing file is found




def onpick(event):
   
    thisline = event.artist
    label = thisline.get_label()
    print(f"You clicked on line: {label}")
    #print(event.ind)
    ax = thisline.axes
    fig = ax.figure
    for line in ax.lines:
        line.set_alpha(.005)
    thisline.set_alpha(1)
    path = thisline.customID
    # store path for once the update loop ends
    #print(path)
    global clickedIDpath
    #store all clicked IDs
    clickedIDpath.add(path)
    

   
    fig.canvas.draw()
    

def main(root_directory, output_directory, gradeExcel):
    

    current_directory = "./"
        
    os.makedirs(output_directory, exist_ok=True)
   
      # Collect all results_all.json file paths.
    file_paths = []
    for dirpath, _, filenames in os.walk(root_directory):
        if "results_raw_data_all.dat" in filenames:
                    file_paths.append(os.path.join(dirpath, "results_raw_data_all.dat"))
                    

    #superGrade, excelller = getGrade(gradeExcel,20301462,"data_noise_25_all_ch_HG_signal")
   # print(superGrade)
    #print("test over")
   # return 0
    
    
    

    print("Enter Test parameter you want displayed, available parameters are: ")

    testParameters = ["data_channel_enable_25", "data_peaking_time_25","data_noise_25_all_ch_HG_signal","data_linearity_25_all_ch_HG","data_noise_25_all_ch_LG_signal","data_linearity_25_all_ch_LG","data_noise_25_sum_x1_signal","data_linearity_25_sum_x1","data_noise_25_sum_x3_signal","data_linearity_25_sum_x3","data_sum_uniformity_25_signal","data_peaking_time_50","data_noise_50_all_ch_HG_signal","data_linearity_50_all_ch_HG","data_noise_50_all_ch_LG_signal","data_linearity_50_all_ch_LG","data_noise_50_sum_x1_signal","data_linearity_50_sum_x1","data_noise_50_sum_x3_signal","data_linearity_50_sum_x3","data_sum_uniformity_50_signal" ]
    print('All or: ')
    print(testParameters)    
    inputString = input()
    
    channelInput = input("Please enter which channel you would like displayed, 0,1,2,3 or All")
    #interactiveSelection = input("Would you like to be able to click on a waveform line and get information about it?")
    deviationSelection = input("Would you like to highlight waveforms that deviate from the mean? Yes/No")
    print("Plot a specific ID? (Yes/No)")
    idCheck = input()
    if idCheck == "Yes":
        print("Please enter IDs one at a time or enter 'Stop' to stop inputting IDs")
        idToCheck = set()
        while True:
            idToChecks = input()
            if idToChecks == 'Stop':
                break
            idToCheck.add(idToChecks)
        
            

        if inputString == "All":
            for parameter in testParameters:
                print(parameter) 
                print(inputString)
                plot_waveform(parameter,file_paths,output_directory, gradeExcel, "All", idToCheck,channelInput,deviationSelection)
        else:      
                plot_waveform(inputString,file_paths,output_directory, gradeExcel, "All", idToCheck,channelInput,deviationSelection)
        
    else: 
        
        print("Please enter chip grade you want displayed, available grades are:")
        grades = "A","B","F","All"
        print(grades)
        chipGradeSelect = input()
       # if chipGradeSelect not in grades:
          #  print("not a valid grade")
          #  return 0
        print(inputString)


        if inputString == "All":
        
            for parameter in testParameters:
                print(parameter) 
                
                plot_waveform(parameter,file_paths,output_directory, gradeExcel, chipGradeSelect,"None",channelInput,deviationSelection)
        elif inputString in testParameters:
         plot_waveform(inputString,file_paths,output_directory, gradeExcel, chipGradeSelect, "None",channelInput,deviationSelection)
     
        else:
            print("Please enter valid string in the test parameters")
     


    

if __name__ == '__main__':
   
    root_directory = r"C:\Users\Maxx\source\repos\alfe_histogram"
    output_directory = r"C:\Users\Maxx\source\repos\alfe_histogram\Output"
    gradeExcel =  r"C:\Users\Maxx\source\repos\alfe_histogram\results.xlsx"

    main(root_directory, output_directory,gradeExcel)





