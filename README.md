# Alfe Histogram

A tool for generating and visualizing histograms for the test data.

## Dependencies
 - Python 3.7 or higher
 - matplotlib
 - numpy
 - python-pptx
 - pandas
## Installation

To get started with the project, clone the repository and install the dependencies:

```bash
git clone https://github.com/cccc04/alfe_histogram.git
cd alfe_histogram
pip3 install matplotlib numpy python-pptx pandas
```

## Usage
1. In `plot_histograms.py`, set the `root_directory` and `output_directory` variables to match the paths of your local data folder and preferred output location.
2. Modify the ranges in `25widths.json` and `50widths.json` to change scale of the x axis if necessary.
3. Run the program
```bash
python3 plot_histograms.py
```
4. In `slides_generation.py`, set `image_folder` to the directory of previously generated histograms and run the program for slides generation
```bash
python3 slides_generation.py
```
5. Slides with Sumx1 and Sumx3 included would position the corresponding images into separate columns. It might be necessary to manually combine them into a single column to achieve a clearer view.
---
