"""Example using GdacClient to search for datasets by time and geospatial bounds and save the output to csv"""
from gdutils import GdacClient
from gdutils.plot import plot_calendar
import datetime
import logging

log_level = getattr(logging, 'INFO')
log_format = '%(asctime)s:%(module)s:%(levelname)s:%(message)s [line %(lineno)d]'
logging.basicConfig(format=log_format, level=log_level)

# Search parameters
dt0 = datetime.datetime(2021, 4, 1, 0, 0, 0)
dt1 = datetime.datetime(2021, 6, 30, 23, 59, 59)
north = None
south = None
east = None
west = None

# Put the search parameters into a dictionary
params = {'min_time': dt0,
          'max_time': dt1,
          'min_lat': south or -90,
          'max_lat': north or 90,
          'min_lon': west or -180,
          'max_lon': east or 180}

# Create an instance of the GdacClient
client = GdacClient()

# Search for the data sets of interest
client.search_datasets(params=params)

# client.datasets is a pandas DataFrame containing the information on the data sets. The information contained in this
# dataframe is over the course of the deployment, not dt0 to dt1
client.datasets.to_html()

# Count the total number of deployments within the dt0:dt1 time window
num_deployments = client.datasets.shape[0]

# Count the number of glider days withing the dt0:dt1 time window
glider_days = client.glider_days_per_yyyymmdd.loc[dt0:dt1].sum()

# count the number of profiles per dataset
profile_count = client.profiles_per_yyyymmdd.loc[dt0:dt1].sum()

# Copy of the datasets data frame
datasets = client.datasets.copy()

# Loop through the datasets, fetch the info url and pull out the desired attributes
sea_names = []
funding_sources = []
for dataset_id, row in datasets.iterrows():

    # Fetch the dataset description from ERDDAP
    info = client.get_dataset_metadata(dataset_id)

    if info.empty:
        continue

    # Find all global NetCDF attributes
    globals = info.loc[info['Variable Name'] == 'NC_GLOBAL']

    # Find the sea_name global attribute
    sea_name_attr = globals.loc[globals['Attribute Name'] == 'sea_name']
    sea_name = 'unknown'
    if not sea_name_attr.empty:
        sea_name = sea_name_attr.Value.iloc[0]
        sea_name = sea_name or 'unknown'
    else:
        logging.warning('{:}: sea_name NC_GLOBAL not found'.format(dataset_id))

    # Find all global attributes that begin with 'acknowledg' as this attribute typically contains the funding sources
    funding_attr = globals.loc[globals['Attribute Name'].str.startswith('acknowledg')]
    funding = 'unknown'
    if not funding_attr.empty:
        funding = funding_attr.Value.iloc[0]
        funding = funding or 'unknown'
    else:
        logging.warning('{:}: acknowledgment NC_GLOBAL not found'.format(dataset_id))

    sea_names.append(sea_name)
    funding_sources.append(funding)

# Add the 2 columns
datasets['deployment_area'] = sea_names
datasets['funding'] = funding_sources

# specify the columns we want in the output when dumping to csv
cols = ['glider',
        'wmo_id',
        'start_date',
        'end_date',
        'num_profiles',
        'days',
        'institution',
        'deployment_area',
        'funding']

datasets.to_csv('/Users/kerfoot/data/gliders/dac/totals/2021_Q2_datasets.csv', columns=cols)