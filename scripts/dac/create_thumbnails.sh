#!/usr/bin/env bash --

PATH=${PATH}:/bin:${HOME}/code;

app=$(basename $0);

# Source bash logging fxns
. logging.sh;
[ "$?" -ne 0 ] && exit 1;

# Usage message
USAGE="
NAME
    $app - 

SYNOPSIS
    $app [h]

DESCRIPTION
    -h
        show help message
";

# Default values for options

# Process options
while getopts "h" option
do
    case "$option" in
        "h")
            echo -e "$USAGE";
            exit 0;
            ;;
        "?")
            echo -e "$USAGE" >&2;
            exit 1;
            ;;
    esac
done

# Remove option from $@
shift $((OPTIND-1));

if [ "$#" -eq 0 ]
then
    error_msg "Please specify a single directory to operate on";
    exit 1;
fi

orig_images=$(find $1 -name "*_largePng.png" 2>/dev/null);
if [ -z "$orig_images" ]
then
    warn_msg "No _largePng.png images found in $1";
    exit 0;
fi

for orig_image in $orig_images
do

    info_msg "Original: $orig_image";

    img_name=$(basename $orig_image .png);
#    thumb_name="$(echo $img_name | sed 's/largePng/tn/g').png";
    thumb_name="${img_name:0:-8}tn.png";
    thumb_path="${1}/${thumb_name}";

    convert $orig_image -thumbnail 200x200 $thumb_path;

done

