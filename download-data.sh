#!/bin/bash

# --- Add these functions to the script ---

# Function to download historical data from Yahoo Finance
download_data() {
  if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Usage: download_data <TICKER> <START_DATE_YYYY-MM-DD> <END_DATE_YYYY-MM-DD> [INTERVAL]"
    echo "INTERVAL can be 1d (daily), 1wk (weekly), 1mo (monthly). Default is 1d."
    return 1
  fi

  ticker=$1
  start_date_str=$2
  end_date_str=$3
  interval=${4:-1d} # Default interval is daily

  # Convert dates to timestamps
  start_timestamp=$(date -d "$start_date_str" +%s)
  end_timestamp=$(date -d "$end_date_str" +%s)

  if ! [[ "$interval" =~ ^(1d|1wk|1mo)$ ]]; then
    echo "Error: Invalid interval. Allowed values are 1d, 1wk, 1mo."
    return 1
  fi

  output_file="${ticker}.csv"

  echo "Downloading ${ticker} data from ${start_date_str} to ${end_date_str} with interval ${interval}..."
  wget --quiet "https://query1.finance.yahoo.com/v7/finance/download/${ticker}?period1=${start_timestamp}&period2=${end_timestamp}&interval=${interval}&events=history&includeAdjustedClose=true" -O "${output_file}"

  if [ $? -eq 0 ]; then
    echo "Data downloaded successfully to ${output_file}"
  else
    echo "Error downloading data for ${ticker}."
  fi
}

# Function to get asset name from Yahoo Finance
get_asset_name() {
  if [ -z "$1" ]; then
    echo "Usage: get_asset_name <TICKER>"
    return 1
  fi
  ticker=$1
  name=$(wget -q -O - "https://finance.yahoo.com/quote/${ticker}" | grep -oP '<title>\K(.*?) - Yahoo Finance</title>' | sed 's/ - Yahoo Finance//')

  if [ -n "$name" ]; then
    echo "Asset name for ${ticker}: ${name}"
  else
    echo "Could not find asset name for ${ticker} or invalid ticker."
  fi
}

# --- Modify the main part of the script to handle options ---

start_date=""
end_date=""
interval=""
ticker=""

while getopts "d:n:s:e:i:h" opt; do
  case $opt in
    d) # Download data
      ticker="$OPTARG"
      ;;
    n) # Get asset name
      get_asset_name "$OPTARG"
      ;;
    s) # Start date for download_data (needs to be handled together with -d, -e, -i)
      start_date="$OPTARG"
      ;;
    e) # End date for download_data (needs to be handled together with -d, -s, -i)
      end_date="$OPTARG"
      ;;
    i) # Interval for download_data (needs to be handled together with -d, -s, -e)
      interval="$OPTARG"
      ;;
    h) # Help message
      echo "Usage: download-data.sh [options]"
      echo "Options:"
      echo "  -d <TICKER> -s <START_DATE_YYYY-MM-DD> -e <END_DATE_YYYY-MM-DD> [-i <INTERVAL>] : Download historical data"
      echo "  -n <TICKER>                                            : Get asset name"
      echo "  -h                                                    : Show help message"
      echo "INTERVAL can be 1d, 1wk, 1mo. Default is 1d."
      exit 0
      ;;
    \?) # Invalid option
      echo "Invalid option: -$OPTARG" >&2
      echo "Use -h for help" >&2
      exit 1
      ;;
  esac
done
shift $((OPTIND-1))

# Process download data if -d option is given along with -s and -e
if [ -n "$start_date" ] && [ -n "$end_date" ] && [ -n "$ticker" ] ; then
  if [ -z "$interval" ]; then
    interval="1d" #default interval if not provided
  fi
  download_data "$ticker" "$start_date" "$end_date" "$interval"
  unset start_date end_date interval ticker #reset variables
fi

# Handle positional arguments if no options were provided for download
if [ -z "$ticker" ] && [ $# -gt 0 ]; then
  ticker=$1
  end_date=$(date +%Y-%m-%d)       # Today as end date
  start_date=$(date -d "yesterday" +%Y-%m-%d) # Yesterday as start date
  interval="1d" # Default interval is daily
  download_data "$ticker" "$start_date" "$end_date" "$interval"
fi
