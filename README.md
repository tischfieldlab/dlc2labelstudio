# About
This is a package to simplify and automate importing a DeepLabCut (DLC) dataset into Label Studio (LS) 
and exporting Label Studio annotation results back into DeepLabCut formats.


# Installation
To install this package, python 3.8 is required. You may create a new environment, or install into an existing environment.

## Create an Anaconda Virtual Environment
```
conda create -n dlc2labelstudio python=3.8
conda activate dlc2labelstudio
```

## Install this repo
For *production* usage:
```
pip install git+https://github.com/tischfieldlab/dlc2labelstudio.git   # if you like to use git over https
pip install git+ssh://git@github.com/tischfieldlab/dlc2labelstudio.git # if you like to use git over ssh
```

OR for *development* usage:
```
git clone https://github.com/tischfieldlab/dlc2labelstudio.git
pip install -e dlc2labelstudio
```

# Usage

## Important Concepts
- We utilize the Label Studio API for integration.
- You must know the endpoint URL (the URL which Label Studio is accessable from)
- You must have an API Access token from Label Studio, accessable from Account and Settings page

## Import DLC data into LS
This command will scan your DLC project for datasets which you have created (searching the `labeled-data` directory of the project root). 
The following will occur:
- Create a project in Label Studio with the name taken from the `Task` field of the DLC configuration.
- Add a labeling configuration to the Label Studio project. The labeling configuration consists of a `KeyPointLabels` with keypoints derived from the `bodyparts` field of the DLC configuration.
- Upload images found in the `labeled-data` directory, and create a task within the Label Studio project. If existing annotations for an image are found, these are also imported along with the labeling task.
- A file named `label-studio-tasks.yaml` will be saved in the DLC project root. The contents of the file describe the mapping between the origional image file name, the Label Studio upload ID for the image, and the uploaded file name as it exists within Label Studio.
```
dlc2labelstudio import-dlc-project --key <access-token> /path/to/DLC/project/root
```

Another case is that since you originally imported your DLC data to Label Studio you have extracted new frames in DLC. To import these new images into label studio, we offer the `--update-project <project-id>` parameter for the `import-dlc-project` command. If this option is passed, a new label studio project will not be created and rather the existing label studio project will be used. Additionally, under this mode the existing images in the label studio project will be scanned and only image in the DLC project, but not in the label studio project will be added to the existing label studio project.

Finally, you may use the `--filter <pattern>` option to filter the images discovered in the DLC project. You may specify this option multiple times, for example `--filter <pattern_1> --filter <pattern_2>`. The patterns can support shell-style wildcards such as `*` (matches everything), `?` (matches a single character), `[seq]` (matches any character in seq), and `[!seq]` (matches any character not in seq). Internally, we use the python function [`fnmatch.fnmatch()`](https://docs.python.org/3/library/fnmatch.html#fnmatch.fnmatch).

## Export LS annotations to DLC
This command will pull annotations from the Label Studio project and save them in a format compatible with DLC.

Final parameter is the Label Studio project ID. Given a project url, such as `http://labelstudio.com/projects/55/data` the project ID would be `55`.

Exported annotations are saved in CSV and HDF5 format in the video-specific directories within the `labeled-data` directory of the DLC project root. If these files already exist, they will be first backed up before the new files are written.
```
dlc2labelstudio export-ls-project --key <access-token> /path/to/DLC/project/root 55
```