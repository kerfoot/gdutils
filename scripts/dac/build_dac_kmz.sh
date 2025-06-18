#! /bin/bash

. ~/.bashrc;

PATH=${PATH}:/bin:${HOME}/code:${HOME}/code/gdutils/scripts/dac;

app=$(basename $0);

# Default values for options
hours=48;
conda_env='gdutils';
json_path='/home/coolgroup/slocum/dac/tracks';
kml_path='/www/home/kerfoot/public_html/gearth/kml/dac';
kml_template='/home/coolgroup/slocum/dac/kml/tracks_template.kml';

# Usage message
USAGE="
NAME
    $app - create kmz containing all DAC gliders that have reported within the last $hours hours

SYNOPSIS
    $app [h] [-t HOURS]

DESCRIPTION

    Create kmz containing all DAC gliders that have reported to the DAC within the last $hours hours

    -h
        show help message
";

# Process options
while getopts "ht:" option
do
    case "$option" in
        "h")
            echo -e "$USAGE";
            exit 0;
            ;;
        "t")
            hours=$OPTARG;
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

if [ ! -d "$json_path" ]
then
    error_msg "Invalid GeoJSON download path: $json_path";
    exit 1;
fi

if [ ! -d "$kml_path" ]
then
    error_msg "Invalid KML path: $kml_path";
    exit 1;
fi

info_msg "GeoJSON download path: $json_path";
info_msg "KML destination path : $kml_path";

old_json=$(ls $json_path/*.json);
if [ -n "$old_json" ]
then
    info_msg "Deleting old GeoJSON tracks in $json_path";
    rm ${json_path}/*.json;
fi

info_msg "Fetching GeoJSON tracks for gliders reporting within the last $hours hours";
download_tracks.sh -m -t $hours -o $json_path;
[ "$?" -ne 0 ] && exit 1;

# Activate the conda environment
info_msg "Activating conda environment: $conda_env";
conda activate $conda_env;

[ "$?" -ne 0 ] && exit 1;

kml_file="${kml_path}/dac_gliders.kml";
kmz_file="${kml_path}/dac_gliders.kmz";

info_msg "Converting GeoJSON files to KML: $kml_file";
recent_datasets_to_kml.py -t $kml_template $json_path/*.json > $kml_file;
if [ "$?" -ne 0 ]
then
    error_msg "Erroring creating KML file $kml_file";
    rm $kml_file;
    exit 1;
fi

info_msg "Deactivating conda environment: $conda_env";
conda deactivate;

info_msg "Zipping KML to KMZ: $kmz_file";
zip $kmz_file $kml_file;

