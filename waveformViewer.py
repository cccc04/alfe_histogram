from asyncio.windows_events import NULL
from calendar import c
import pickle
import numpy as np
import matplotlib.pyplot as plt
import os
import pandas as pd


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

    
        
       



def dim(a):
    if not type(a) == list:
        return []
    return [len(a)] + dim(a[0])

def plot_waveform(dataset_name, file_paths, output_directory, excelSheetGrades):
    
    for channel in range(4):
        plt.figure(figsize=(12, 6))  # One figure

        for file_path in file_paths:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
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
            grade, excelSheetGrades = getGrade(excelSheetGrades,ID, dataset_name )
            
            if grade == "A":
                colorGrade = "Green"
            elif grade == "B":
                colorGrade = "Yellow"
            elif grade == "F":
                colorGrade = "Red"
            else:
                colorGrade = "Blue"
                print(ID)
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
                           print("\n")
                            

                    plt.plot(x_axis, measured, color = colorGrade, label='Measured', linewidth = .8)
                    #plt.plot(x_axis, expected, label='Expected')
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
                plt.plot(dataset, color = colorGrade, label=f'{os.path.basename(file_path)}', linewidth = .8)

            # === 2D ===
            elif dataset.ndim == 2:
                for i, channel in enumerate(dataset):
                    plt.plot(channel, color = colorGrade, label=f'{os.path.basename(file_path)} - Ch {i}', linewidth = .8)

            # === 3D ===
            elif dataset.ndim == 3:
                
    
                     # Average over blocks for this channel
                 avg_waveform = np.mean(dataset[:, channel, :], axis=0)
        
                 label = f'{os.path.basename(file_path)} - Ch {channel}'
                 plt.plot(avg_waveform, color = colorGrade, label=label, linewidth = .8)


            else:
                print(f"Unsupported data dimensions: {dataset.ndim}D")
                continue

        plt.xlabel("Sample Index")
        plt.ylabel("Amplitude")
        plt.grid(True)
        plt.title(f"Waveform: {dataset_name}")
        #plt.legend(fontsize='small', ncol=2)
    
        # Save and show
        filename = f"{dataset_name}_graph.png"
        plt.savefig(os.path.join(output_directory, filename), dpi=300)
        
     
        #plt.show()

        plt.close()


#get the excel sheet to a simple matrix, one column with id, other chip grade, sorted so faster search
def getGrade(gradeExcel, ID, name):
    import pandas as pd
    import numpy as np

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
    print(f"[DEBUG] testKeys: {testKeys} (type: {type(testKeys)})")

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
    testParameters = ["data_channel_enable_25", "data_peaking_time_25","data_noise_25_all_ch_HG_signal","data_linearity_25_all_ch_HG","data_noise_25_all_ch_LG_signal","data_linearity_25_all_ch_LG","data_noise_25_sum_x1_signal","data_linearity_25_sum_x1","data_noise_25_sum_x3_signal","data_linearity_25_sum_x3","data_sum_uniformity_25_signal","data_peaking_time_50","data_noise_50_all_ch_HG_signal","data_linearity_50_all_ch_HG","data_noise_50_all_ch_LG_signal","data_linearity_50_all_ch_LG","data_noise_50_sum_x1_signal","data_linearity_50_sum_x1","data_noise_50_sum_x3_signal","data_linearity_50_sum_x3","data_sum_uniformity_50_signal" ]
    for parameter in testParameters:
        print(parameter) 
        plot_waveform(parameter,file_paths,output_directory, gradeExcel)
   # plot_waveform("data_linearity_50_sum_x1",file_paths,output_directory, gradeExcel)


    

if __name__ == '__main__':
   
    root_directory = r"C:\Users\Maxx\source\repos\alfe_histogram"
    output_directory = r"C:\Users\Maxx\source\repos\alfe_histogram\Output"
    gradeExcel = r"C:\Users\Maxx\source\repos\alfe_histogram\results.xlsx"

    main(root_directory, output_directory,gradeExcel)





