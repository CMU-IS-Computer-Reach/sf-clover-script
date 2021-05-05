# sf-clover-script

### Initial setup
```
git clone https://github.com/CMU-IS-Computer-Reach/sf-clover-script.git
cd sf-clover-script
python3 -m venv .
source bin/activate
pip install -r requirements.txt
```

### Running the script
First, export Customers, Orders, and Transactions (Payments) from Clover. Make sure that Orders and Payments are limited to the appropriate date range. Drag the downloaded CSV files into this directory and rename them to `customers.csv`, `orders.csv`, and `payments.csv`, respectively.

Before running the script, make sure the virtualenv is active.
```
source bin/activate
```
If you want to run on a test SF instance, make sure you have a file `.env.test` in this directory with the following format. For a prod SF instance, have `.env`:
```
SF_USERNAME=<your Salesforce username>
SF_PASSWORD=<your Salesforce password>
SF_TOKEN=<your Salesforce security token>
```
To see how to run the script, run `python3 script.py -h`. Here are some ways to run the script:
```
python3 script.py -t 05-05-2021         # Run with a test SF instance from May 5, 2021 til today
python3 script.py 04-20-2021 05-05-2021 # Run with a prod SF instance from April 20, 2021 til May 5, 2021
```

