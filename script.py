# script.py: populate Salesforce with data exported from Clover
# Write customers who joined since the last time this script was run (or over the last
# DEFAULT_NUM_DAYS_AGO days). Log output to LOG_FILE and make a copy of the csv in
# "CSV_HISTORY_DIR/<today's date>/customers.csv".

import os
import sys
import datetime as dt
import pandas as pd
from shutil import copyfile
from simple_salesforce import Salesforce
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Define file names and defaults
ORDERS_CSV_FILE      = 'orders.csv'       # Orders csv file exported from Clover
PAYMENTS_CSV_FILE    = 'payments.csv'     # Payments csv file exported from Clover
                                          # Orders and Payments should be exported with same date range 

CUSTOMERS_CSV_FILE   = 'customers.csv'    # Customers csv file exported from Clover
CSV_HISTORY_DIR      = 'csv_history'      # Directory to which csvs are copied
LAST_INVOKED_FILE    = 'last_invoked.txt' # File storing the date this script was last run
LOG_FILE             = 'log.txt'          # File to which this script appends logs
DEFAULT_NUM_DAYS_AGO = 7                  # Number of days ago to filter customers if
                                          #   LAST_INVOKED_FILE doesn't exist
DATE_FORMAT          = '%m-%d-%Y'         # Date format stored in LAST_INVOKED_FILE
DATETIME_FORMAT      = '%c'               # Datetime format stored in LOG_FILE

# Function to print to console and write to LOG_FILE
def log(message):
    print(message, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(message)

# Record script start time
start_time = dt.datetime.now()

# TODO: Parse commandline arguments

# Initialize SF connection
sf = Salesforce(
    username       = os.environ['SF_USERNAME'],
    password       = os.environ['SF_PASSWORD'],
    security_token = os.environ['SF_TOKEN'],
    domain         = 'test'
)

# Load csvs
try:
    orders = pd.read_csv(ORDERS_CSV_FILE)
    payments = pd.read_csv(PAYMENTS_CSV_FILE)
    customers = pd.read_csv(CUSTOMERS_CSV_FILE)
    print('Files loaded!')
except FileNotFoundError:
    print('[ERROR] CSV file not found!')
    sys.exit()

# Drop irrelevant columns
   orders.drop(['Invoice Number', 'Order Number', 'Order Employee ID', 
                'Order Employee Name', 'Order Employee Custom ID', 
                'Currency', 'Tax Amount', 'Tip', 'Service Charge',
                'Discount', 'Refunds Total', 'Manual Refunds Total', 
                'Credit Card Auth Code', 'Credit Card Transaction ID', 
                'Tender'], axis=1, inplace=True)
 payments.drop(['Payment ID', 'Transaction #', 'Note', 'Tender', 'Result',
                'Order Date', 'External Payment ID', 'Invoice Number', 
                'Card Auth Code', 'Card Brand', 'Card Number', 'Card Entry Type', 
                'Currency', 'Tax Amount', 'Tip Amount', 'Service Charge Amount', 
                'Payment Employee ID', 'Payment Employee Name', 
                'Payment Employee Custom ID', 'Order Employee ID',
                'Order Employee Name', 'Order Employee Custom ID', 'Device',
                '# Refunds', 'Refund Amount'], axis=1, inplace=True)
customers.drop(['Customer ID', 'Address Line 1', 'Address Line 2',
                'Address Line 3', 'City', 'State / Province',
                'Postal / Zip Code', 'Country', 'Marketing Allowed',
                'Additional Addresses'], axis=1, inplace=True)

# Connect Order and Payment Data Together
transactions = payments.merge(orders, on='Order ID', how='inner')
transactions.insert(1, "AccountID", ['Curbside Sales (Outgoing)']*len(trans.index), True)
transactions.insert(2, "Site_Served__c", ['Curbside Sales (Outgoing)']*len(trans.index), True)
transactions.rename(columns= {'Customer Name':'Site_Contact__c', 'Order Payment State':'StageName'}, inplace=True)

# TODO: Concatanate Name, CRid, Date, and Amount as David lays it out,
#        this information goes into a 'Name' column for SF, then drop other cols

# Filter out customers by join date
customers_start_date = dt.date.today() - dt.timedelta(days=DEFAULT_NUM_DAYS_AGO)
customers_end_date = dt.date.today()
try:
    with open(LAST_INVOKED_FILE) as f:
        last_invoked_date_str = f.read(10)
        customers_start_date = dt.datetime.strptime(last_invoked_date_str, DATE_FORMAT).date() \
                               + dt.timedelta(days=1) # Add a day so there's no overlap between runs
except FileNotFoundError:
    print("LAST_INVOKED_FILE ({}) not found, keeping new customers since {}"
          .format(LAST_INVOKED_FILE, customers_start_date.strftime(DATE_FORMAT)))

customers_limited = customers[
    pd.to_datetime(customers['Customer Since']).dt.date >= customers_start_date]
customers = customers_limited[
    pd.to_datetime(customers_limited['Customer Since']).dt.date <= customers_end_date]

# Clean customers data
customers.drop('Customer Since', axis=1, inplace=True)
customers.columns = ['FirstName', 'LastName', 'Phone', 'Email']
customers.fillna('', inplace=True)

# Write records to SF
log("{} (insert customers from {} - {}): ".format(
    start_time.strftime(DATETIME_FORMAT),
    customers_start_date.strftime(DATE_FORMAT),
    customers_end_date.strftime(DATE_FORMAT)))

data = customers.to_dict('records')
num_skipped = 0
for customer in data:
    try:
        sf.Contact.create(customer)
    except:
        log("\tCould not insert customer {} {}\n".format(customer.FirstName, customer.LastName))
        num_skipped += 1

# Update LAST_INVOKED_FILE
with open(LAST_INVOKED_FILE, 'w') as f:
    f.write(customers_end_date.strftime(DATE_FORMAT))

# Make copies of csvs
dest_csv_path = "{}/{}/customers.csv".format(CSV_HISTORY_DIR, start_time.strftime(DATE_FORMAT))
os.makedirs(os.path.dirname(dest_csv_path), exist_ok=True)
copyfile(CUSTOMERS_CSV_FILE, dest_csv_path)

# Append log to LOG_FILE
num_written = len(data) - num_skipped
log("{} records written, {} skipped\n\n".format(num_written, num_skipped))
