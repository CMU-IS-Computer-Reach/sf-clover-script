import os
import pandas as pd
import datetime as dt
from simple_salesforce import Salesforce
from dotenv import load_dotenv

load_dotenv()

CUSTOMERS_CSV_FILE = 'customers.csv'
LAST_INVOKED_FILE  = 'last_invoked.txt'

# Set up SF connection
sf = Salesforce(
  	username       = os.environ['SF_USERNAME'],
  	password       = os.environ['SF_PASSWORD'],
  	security_token = os.environ['SF_TOKEN'],
    domain         = 'test'
)

# Load csvs
try:
    customers = pd.read_csv(CUSTOMERS_CSV_FILE)
    print('Files loaded!')
except FileNotFoundError:
    print('CSV file names not changed properly')

# Drop irrelevant columns
customers.drop(['Customer ID', 'Address Line 1', 'Address Line 2', 'Address Line 3',
                'City', 'State / Province', 'Postal / Zip Code',
                'Country', 'Marketing Allowed', 'Additional Addresses'], axis=1, inplace=True)

# Filter out customers already in SF
customers_start_date = dt.date.today() - dt.timedelta(days=14)
customers_end_date = dt.date.today()
try:
		with open(LAST_INVOKED_FILE) as f:
				last_invoked_date_str = f.read(10)
				customers_start_date = dt.datetime.strptime(last_invoked_date_str, '%m/%d/%Y').date() + dt.timedelta(days=1)
except FileNotFoundError:
		print("LAST_INVOKED_FILE ({}) not found, keeping new customers since {}".format(LAST_INVOKED_FILE, customers_start_date.strftime('%m/%d/%Y')))

customers_limited = customers[(pd.to_datetime(customers['Customer Since']).dt.date >= customers_start_date)]
customers = customers_limited[(pd.to_datetime(customers_limited['Customer Since']).dt.date <= customers_end_date)]

# Clean customers data
customers.drop('Customer Since', axis=1, inplace=True)
customers.columns = ['FirstName', 'LastName', 'Phone', 'Email']

# Replace invalid values
customers.fillna('', inplace=True)

# Write records to SF
data = customers.to_dict('records')
for customer in data:
    sf.Contact.create(customer)

# Update LAST_INVOKED_FILE
with open(LAST_INVOKED_FILE, 'w') as f:
    f.write(customers_end_date.strftime('%m/%d/%Y'))

print("All done ({} records written)!".format(len(data)))

