#! /usr/bin/env bash --

. ~/.bashrc;

PATH="${PATH}:/bin:${HOME}/code:${HOME}/code/gdutils/scripts/dac";

# DAC imagery root
imagery_root='/Users/kerfoot/Sites/dac/status/api/data/datasets';

app=$(basename $0);

# Source bash logging fxns
. logging.sh;
[ "$?" -ne 0 ] && exit 1;

# Default values for options
num_minutes=60;
conda_env='gdutils';

# Usage message
USAGE="
NAME
    $app - download DAC imagery

SYNOPSIS
    $app [hxm MINUTES] [dataset_id1 dataset_id2...]

    Download map, profile and time-series imagery from DAC datasets that have updated within the last $num_minutes
    minutes

DESCRIPTION
    -h
        show help message
    
    -m MINUTES
        select datasets that have updated within the last MINUTES minutes

    -x
        Print the dataset ids but do not download any imagery
";

# Process options
while getopts "hxm:" option
do
    case "$option" in
        "h")
            echo -e "$USAGE";
            exit 0;
            ;;
        "x")
            debug=1;
            ;;
        "m")
            num_minutes=$OPTARG;
            ;;
        "?")
            echo -e "$USAGE" >&2;
            exit 1;
            ;;
    esac
done

# Remove option from $@
shift $((OPTIND-1));

if [ ! -d "$imagery_root" ]
then
    error_msg "Invalid imagery root specified: $imagery_root";
    exit 1;
fi

# Activate the conda environment
conda activate $conda_env;

[ "$?" -ne 0 ] && exit 1;

if [ "$#" -eq 0 ]
then
    num_hours=$(( num_minutes/60 ));
    
    dataset_ids=$(search_datasets.py --hours $num_hours | grep -v dataset_id);
    if [ -z "$dataset_ids" ]
    then
        warn_msg "No datasets found that have updated within the last $num_minutes minutes";
        exit 0
    fi
else
    dataset_ids="$@";
fi

eovs='temperature salinity density conductivity';

for dataset_id in $dataset_ids
do

    if [ -n "$debug" ]
    then
        debug_msg "Dataset ID: $dataset_id";
        continue;
    fi

    info_msg "Checking dataset: $dataset_id";

    # Check to see if the dataset exists on the ERDDAP server
    is_dataset=$(get_dataset.py $dataset_id);
    [ "$?" -eq 1 ] && continue;

    info_msg "Getting imagery for dataset $dataset_id";

    dataset_path="${imagery_root}/$dataset_id";
    info_msg "Dataset path: $dataset_path";
    [ ! -d "$dataset_path" ] && warn_msg "Dataset path does not exist" && continue;

    imagery_path="${dataset_path}/imagery";
    info_msg "Imagery path: $imagery_path";
    if [ ! -d "$imagery_path" ]
    then
        info_msg "Creating imagery path: $imagery_path";
        mkdir -m 755 $imagery_path;
        [ "$?" -ne 0 ] && continue;
    fi

    # Create map figure
    map_path="${imagery_path}/maps";
    info_msg "Map path: $map_path";
    if [ ! -d "$map_path" ]
    then
        info_msg "Creating maps path: $map_path";
        mkdir -m 755 $map_path;
        [ "$?" -ne 0 ] && continue;
    fi
    info_msg "Requesting map...";
    map_img=$(plot_dataset_map.py -d $map_path --format largePng $dataset_id);
    if [ -f "$map_img" ]
    then
        info_msg "Map downloaded: $map_img";
        create_map_thumbs=1;
    else
        error_msg "Failed to download map";
        continue;
    fi
    # Create thumbs
    [ -n "$create_map_thumbs" ] && info_msg "Creating maps thumbnails..." && create_thumbnails.sh $map_path;
#    info_msg "Requesting map thumbnail...";
#    map_img=$(plot_dataset_map.py -d $map_path --format smallPng --no-legend $dataset_id);
#    if [ -f "$map_img" ]
#    then
#        info_msg "Map thumbnail downloaded: $map_img";
#    else
#        error_msg "Failed to download map thumbnail";
#        continue;
#    fi
    
    erddap_path="${imagery_path}/erddap";
    info_msg "ERDDAP imagery path: $erddap_path";
    if [ ! -d "$erddap_path" ]
    then
        info_msg "Creating erddap path: $erddap_path";
        mkdir -m 755 $erddap_path;
        [ "$?" -ne 0 ] && continue;
    fi

    latest_path="${erddap_path}/latest";
    synoptic_path="${erddap_path}/synoptic";

    # Create latest profiles imagery
    latest_profiles_path="${latest_path}/profiles"; 
    info_msg "Latest profiles path: $latest_profiles_path";
    if [ ! -d "$latest_profiles_path" ]
    then
        info_msg "Creating latest profiles path: $latest_profiles_path";
        mkdir -pm 755 $latest_profiles_path;
        [ "$?" -ne 0 ] && continue;
    fi

    for eov in $eovs
    do
        info_msg "Requesting latest $eov profiles...";
        img=$(plot_dataset_variable.py --profiles --hours 24 -d $latest_profiles_path --format largePng $dataset_id $eov);
        if [ -f "$img" ]
        then
            info_msg "Image downloaded: $img";
            create_latest_profiles_thumbs=1;
        else
            error_msg "Failed to download image";
        fi
#        info_msg "Requesting latest $eov thumbnail profiles...";
#        img=$(plot_dataset_variable.py --profiles --hours 24 -d $latest_profiles_path --format smallPng --no-legend $dataset_id $eov);
#        if [ -f "$img" ]
#        then
#            info_msg "Thumbnail downloaded: $img";
#        else
#            error_msg "Failed to download thumbnail";
#        fi
    done
    # Create thumbs
    [ -n "$create_latest_profiles_thumbs" ] && info_msg "Creating latest profiles thumbs..." && create_thumbnails.sh $latest_profiles_path;

    # Create lastest time-series imagery
    latest_ts_path="${latest_path}/timeseries"; 
    info_msg "Latest time-series path: $latest_ts_path";
    if [ ! -d "$latest_ts_path" ]
    then
        info_msg "Creating latest time-series path: $latest_ts_path";
        mkdir -pm 755 $latest_ts_path;
        [ "$?" -ne 0 ] && continue;
    fi

    for eov in $eovs
    do
        info_msg "Requesting latest $eov time-series...";
        img=$(plot_dataset_variable.py --hours 24 -d $latest_ts_path --format largePng $dataset_id $eov);
        if [ -f "$img" ]
        then
            info_msg "Image downloaded: $img";
            create_latest_ts_thumbs=1;
        else
            error_msg "Failed to download image";
        fi
#        info_msg "Requesting latest $eov thumbnail time-series...";
#        img=$(plot_dataset_variable.py --hours 24 -d $latest_ts_path --format smallPng --no-legend $dataset_id $eov);
#        if [ -f "$img" ]
#        then
#            info_msg "Thumbnail downloaded: $img";
#        else
#            error_msg "Failed to download thumbnail";
#        fi
    done
    # Create thumbs
    [ -n "$create_latest_ts_thumbs" ] && info_msg "Creating latest time-series thumbs..." && create_thumbnails.sh $latest_ts_path;
    
    # Create synoptic time-series imagery
    synoptic_ts_path="${synoptic_path}/timeseries"; 
    info_msg "Synoptic time-series path: $synoptic_tss_path";
    if [ ! -d "$synoptic_ts_path" ]
    then
        info_msg "Creating synoptic time-series path: $synoptic_ts_path";
        mkdir -pm 755 $synoptic_ts_path;
        [ "$?" -ne 0 ] && continue;
    fi

    for eov in $eovs
    do
        info_msg "Requesting synoptic $eov time-series...";
        img=$(plot_dataset_variable.py --all -d $synoptic_ts_path --format largePng $dataset_id $eov);
        if [ -f "$img" ]
        then
            info_msg "Image downloaded: $img";
            create_synoptic_ts_thumbs=1;
        else
            error_msg "Failed to download image";
        fi
#        info_msg "Requesting synoptic $eov thumbnail time-series...";
#        img=$(plot_dataset_variable.py --hours 24 -d $synoptic_ts_path --format smallPng --no-legend $dataset_id $eov);
#        if [ -f "$img" ]
#        then
#            info_msg "Thumbnail downloaded: $img";
#        else
#            error_msg "Failed to download thumbnail";
#        fi
    done
    # Create thumbs
    [ -n "$create_synoptic_ts_thumbs" ] && info_msg "Creating synoptic time-series thumbs..." && create_thumbnails.sh $synoptic_ts_path;

done

conda deactivate;

