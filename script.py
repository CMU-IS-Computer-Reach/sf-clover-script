# script.py: populate Salesforce with data exported from Clover
# Write customers who joined since the last time this script was run (or over the last
# DEFAULT_NUM_DAYS_AGO days). Log output to LOG_FILE and make a copy of the csv in
# "CSV_HISTORY_DIR/<timestamp>/customers.csv".
#
# Required environment variables
# SF_USERNAME : Salesforce username
# SF_PASSWORD : Salesforce password
# SF_TOKEN    : security token

import argparse
import os
import sys
import re
import datetime as dt
import pandas as pd
from datetime import datetime
from shutil import copyfile
from simple_salesforce import Salesforce
from dotenv import load_dotenv

# Define file names and defaults
ORDERS_CSV_FILE      = 'orders.csv'       # Orders csv file exported from Clover
PAYMENTS_CSV_FILE    = 'payments.csv'     # Payments csv file exported from Clover
CUSTOMERS_CSV_FILE   = 'customers.csv'    # Customers csv file exported from Clover
CSV_HISTORY_DIR      = 'csv_history'      # Directory to which csvs are copied
LOG_FILE             = 'log.txt'          # File to which this script appends logs
DATE_FORMAT          = '%m-%d-%Y'         # Date format used by the script
DATETIME_FORMAT      = '%c'               # Datetime format stored in LOG_FILE

# Function to print to console and write to LOG_FILE
def log(message):
    print(message, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(message)

# Record script start time
start_time = dt.datetime.now()

# Parse commandline arguments
parser = argparse.ArgumentParser(description='Write data from Clover CSV files to SF.')
parser.add_argument('start_date', help='start of date range (mm-dd-yyyy)')
parser.add_argument('end_date', nargs='?', default=start_time.strftime(DATE_FORMAT),
    help='end of date range (mm-dd-yyyy)')
parser.add_argument('-t', dest='test', action='store_true',
    help='flag for running on a test SF instance (must have a valid .env.test file)')

args = parser.parse_args()

# Validate arguments
if re.match(r'\d{2}-\d{2}-\d{4}$', args.start_date) is None or \
    re.match(r'\d{2}-\d{2}-\d{4}$', args.end_date) is None:
    print('[ERROR] Dates must be of the form mm-dd-yyyy')
    sys.exit()

should_proceed = input("Running for dates {} through {} in {} (y/n): "
                       .format(args.start_date, args.end_date, 'test' if args.test else 'prod'))
if should_proceed[0] != 'y':
    sys.exit()

# Load environment variables
if args.test:
    load_dotenv('.env.test')
else:
    load_dotenv()

# Initialize SF connection
connection_args = {
    'username'       : os.environ['SF_USERNAME'],
    'password'       : os.environ['SF_PASSWORD'],
    'security_token' : os.environ['SF_TOKEN']
}

if args.test:
    connection_args['domain'] = 'test'

sf = Salesforce(**connection_args)

# Lookup record type "Item Shipment"
data = sf.query_all("SELECT Id FROM RecordType WHERE Name = 'Item Shipment' LIMIT 1")
recordtype_id = None
if data['totalSize'] == 0:
    log('No RecordType found\n')
    sys.exit()
else:
    recordtype_id = data['records'][0]['Id']

# Lookup organization "Curbside Sales (Outgoing)"
data = sf.query_all("SELECT Id FROM Account WHERE Name = 'Curbside Sales (Outgoing)' LIMIT 1")
org_id = None
if data['totalSize'] == 0:
    log('No organization found\n')
    sys.exit()
else:
    org_id = data['records'][0]['Id']

# Load csvs
try:
    orders = pd.read_csv(ORDERS_CSV_FILE)
    payments = pd.read_csv(PAYMENTS_CSV_FILE)
    customers = pd.read_csv(CUSTOMERS_CSV_FILE)
    print('CSV files loaded!')
except FileNotFoundError:
    print('[ERROR] CSV file not found!')
    sys.exit()

# Drop irrelevant columns
orders.drop(['Invoice Number', 'Order Number', 'Order Employee ID', 'Order Employee Name',
             'Order Employee Custom ID', 'Currency', 'Tax Amount', 'Tip', 'Service Charge',
             'Discount', 'Refunds Total', 'Manual Refunds Total', 'Credit Card Auth Code',
             'Credit Card Transaction ID', 'Tender', 'Order Date', 'Order Total', 'Payments Total',
             'Payment Note'], axis=1, inplace=True)

payments.drop(['Payment ID', 'Transaction #', 'Note', 'Tender', 'Result', 'Order Date',
               'External Payment ID', 'Invoice Number', 'Card Auth Code', 'Card Brand',
               'Card Number', 'Card Entry Type', 'Currency', 'Tax Amount', 'Tip Amount',
               'Service Charge Amount', 'Payment Employee ID', 'Payment Employee Name',
               'Payment Employee Custom ID', 'Order Employee ID', 'Order Employee Name',
               'Order Employee Custom ID', 'Device', '# Refunds', 'Refund Amount'], axis=1,
               inplace=True)

customers.drop(['Customer ID', 'Address Line 1', 'Address Line 2', 'Address Line 3', 'City',
                'State / Province', 'Postal / Zip Code', 'Country', 'Marketing Allowed',
                'Additional Addresses'], axis=1, inplace=True)

# Connect Order and Payment data together
transactions = payments.merge(orders, on='Order ID', how='inner')

# Stage transaction data for SF
transactions.fillna('', inplace=True)

if org_id is not None:
    transactions.insert(1, "AccountId", [org_id]*len(transactions.index), True)
    transactions.insert(2, "Site_Served__c", [org_id]*len(transactions.index), True)

if recordtype_id is not None:
    transactions.insert(3, 'RecordTypeId', [recordtype_id]*len(transactions.index), True)

# Create Donation and Shipment record names
shipments = transactions.to_dict('records')
donation_shipment_names = []

for record in shipments:
    name = 'Missing Info' if record['Customer Name'] == '' else record['Customer Name']    
    amt = '$' + str(record['Amount']) + '0'
    datestring = record['Payment Date'][3:6] + ' ' + record['Payment Date'][:2] + ", " + \
                 record['Payment Date'][7:11]
    date_time_obj = datetime.strptime(datestring, '%b %d, %Y')
    date = dt.datetime.strftime(date_time_obj, '%m/%d/%Y')
    crids = re.sub("[^0-9, ]", "", record['Note']).strip()
    if crids == '':
        crids = 'Not Found'
    donation_shipment_names.append(name + ' - Shipment CRID(s): ' + crids + ' '+ date + ' = ' + amt)

transactions.insert(4, 'Name', donation_shipment_names, True)
transactions.rename(columns= {'Order Payment State':'StageName', 'Payment Date': 'CloseDate'},
                    inplace=True)
transactions.drop(['Customer Name', 'Order ID', 'Note'], axis=1, inplace=True)

# Filter out customers by join date
customers_start_date = dt.datetime.strptime(args.start_date, DATE_FORMAT).date()
customers_end_date = dt.datetime.strptime(args.end_date, DATE_FORMAT).date()

customers_limited = customers[
    pd.to_datetime(customers['Customer Since']).dt.date >= customers_start_date]
customers = customers_limited[
    pd.to_datetime(customers_limited['Customer Since']).dt.date <= customers_end_date]

# Clean customers data
customers.drop('Customer Since', axis=1, inplace=True)
customers.columns = ['FirstName', 'LastName', 'Phone', 'Email']
customers.fillna('', inplace=True)
customers.insert(1, 'AccountId', [org_id]*len(customers.index), True)

# Write records to SF
log("[{}] {} ({} - {})\n".format(
    'TEST' if args.test else 'PROD',
    start_time.strftime(DATETIME_FORMAT),
    customers_start_date.strftime(DATE_FORMAT),
    customers_end_date.strftime(DATE_FORMAT)))

log('Transactions:\n')
transaction_data = transactions.to_dict('records')
transactions_skipped = 0
for transaction in transaction_data:
    try:
        transaction['CloseDate'] = dt.datetime.strptime(transaction['CloseDate'],
                                                        '%d-%b-%Y %I:%M %p %Z').isoformat()
        sf.Opportunity.create(transaction)
        log("\tInserted transaction '{}'\n".format(transaction['Name']))
    except Exception as e:
        log("\tCould not insert transaction '{}'\n\tError: {}\n"
            .format(transaction['Name'], str(e)))
        transactions_skipped += 1

log('Customers:\n')
customer_data = customers.to_dict('records')
customers_skipped = 0
for customer in customer_data:
    try:
        sf.Contact.create(customer)
        log("\tInserted customer {} {}\n".format(customer['FirstName'], customer['LastName']))
    except Exception as e:
        log("\tCould not insert customer {} {}\n\tError: {}\n"
            .format(customer['FirstName'], customer['LastName'], str(e)))
        customers_skipped += 1

# Make copies of csvs
dest_csv_path = "{}/{}/".format(CSV_HISTORY_DIR, start_time.isoformat())
os.makedirs(os.path.dirname(dest_csv_path + 'input/'), exist_ok=True)
copyfile(ORDERS_CSV_FILE, dest_csv_path + 'input/orders.csv')
copyfile(PAYMENTS_CSV_FILE, dest_csv_path + 'input/payments.csv')
copyfile(CUSTOMERS_CSV_FILE, dest_csv_path + 'input/customers.csv')

os.makedirs(os.path.dirname(dest_csv_path + 'actual/'), exist_ok=True)
customers.to_csv(dest_csv_path + 'actual/customers.csv')
transactions.to_csv(dest_csv_path + 'actual/transactions.csv')

# Log results of run
customers_written = len(customer_data) - customers_skipped
log("{} customer records written, {} skipped\n".format(customers_written, customers_skipped))

transactions_written = len(transaction_data) - transactions_skipped
log("{} transaction records written, {} skipped\n\n"
    .format(transactions_written, transactions_skipped))
