#! /bin/bash --

. ~/.bashrc;

PATH=${PATH}:/bin:${HOME}/code:${HOME}/code/gdutils/scripts/dac;

app=$(basename $0);

# Default values for options
hours=24;
conda_env='gdutils';
output_dir=$(realpath .);

# Usage message
USAGE="
NAME
    $app - Download data set metadata and geojson tracks from the IOOS Glider DAC ERDDAP server

SYNOPSIS

    Searches for and download data set metadata and daily decimated geojson tracks from the 
    IOOS Glider DAC ERDDAP server for data sets that have updated within the last $hours hours.
    Files are written to:

        $output_dir

    by default.

    $app [h]

DESCRIPTION
    -h
        show help message

    -t HOURS
        Search for data sets that have updated within the last HOURS. Default is $hours hours

    -o PARENT_DIRECTORY
        Specify an alternate parent directory for writing 

    -m
        Include ERDDAP data set metadata

    -a
        Write all profile positions to the GeoJSON object
";

# Process options
while getopts "ht:o:ma" option
do
    case "$option" in
        "h")
            echo -e "$USAGE";
            exit 0;
            ;;
        "t")
            hours=$OPTARG;
            ;;
        "o")
            output_dir=$OPTARG;
            ;;
        "m")
            metadata=1;
            ;;
        "a")
            all=1;
            ;;
        "?")
            echo -e "$USAGE" >&2;
            exit 1;
            ;;
    esac
done

# Remove option from $@
shift $((OPTIND-1));

# Load logging routines
. logging.sh;
[ "$?" -ne 0 ] && exit 1;

if [ ! -f "search_datasets.py" ]
then
    error_msg "Cannot locate search_datasets.py";
    exit 1;
fi

if [ ! -f "get_dataset_track.py" ]
then
    error_msg "Cannot locate get_dataset_track.py";
    exit 1;
fi

if [ ! -d "$output_dir" ]
then
    error_msg "Invalid parent destination directory specified: $output_dir";
    exit 1;
fi

info_msg "Writing to destination directory: $output_dir";

# Activate the conda environment
info_msg "Activating conda environment: $conda_env";
conda activate $conda_env;

[ "$?" -ne 0 ] && exit 1;

info_msg "Searching for datasets that have updated within the last $hours hours";

dataset_ids=$(search_datasets.py --hours $hours | grep -v -i dataset | tr '\n' ' ');

for dataset_id in $dataset_ids
do
    info_msg "Downloading $dataset_id";
    json_file="${output_dir}/${dataset_id}_track.json";

    if [ -n "$metadata" ]
    then
        if [ -n "$all" ]
        then
            info_msg "Downloading full resolution tracks with ERDDAP metadata";
            get_dataset_track.py --metadata $dataset_id > $json_file;
        else
            info_msg "Downloading daily averaged tracks with ERDDAP metadata";
            get_dataset_track.py --daily --metadata $dataset_id > $json_file;
        fi
    else
        if [ -n "$all" ]
        then
            info_msg "Downloading full resolution tracks without ERDDAP metadata";
            get_dataset_track.py $dataset_id > $json_file;
        else
            info_msg "Downloading daily averaged tracks without ERDDAP metadata";
            get_dataset_track.py --daily $dataset_id > $json_file;
        fi
    fi

done
conda deactivate;

