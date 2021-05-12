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

Before running the script, **make sure the virtualenv is active**.
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

### Script output
Everything you see on console while the script is running will appear in `log.txt`. Additionally, the `customers.csv`, `orders.csv`, and `payments.csv` will be saved to `csv_history/<t>/input` while the actual rows that the script tried writing to Salesforce are saved to `csv_history/<t>/actual` (`customers.csv` and `transactions.csv`), where `<t>` represents the time at which the script was invoked. Note that `customers.csv`, `orders.csv`, and `payments.csv` are removed if the script runs to completion.

### Troubleshooting
Generally speaking, errors outputted by the script are useful to hone in on the source of the problem. But here are points at which something might have went wrong:
- Missing/invalid Salesforce credentials (double check your .env and .env.test files)
- Connection to Salesforce failed due to maintenance (just wait for a little bit although this is unlikely)
- Bad customer email format will cause a skip (ie: abc@@computerreach.org)
- Bad request (maybe there was a breaking change to the Salesforce API; see if anyone is [complaining about this](https://github.com/simple-salesforce/simple-salesforce/issues) but this could probably be fixed by upgrading one of the script's dependencies - see below)

### Upgrading dependencies
If at any point you get some errors about bad requests to Salesforce or something, you can try to upgrade `simple-salesforce`, the main dependency of the script.
1. Go into `requirements.txt` and change the version (x.xx.xx) to the [latest](https://pypi.org/project/simple-salesforce/)
2. `source bin/activate`
3. `pip install -r requirements.txt`

### Making hotfixes
If you want to modify the script, just follow the subheadings in the script. Non-trivial changes might require you to dig a bit into how to work with `pandas` and `simple-salesforce` but the specifics of those are outside the scope of this doc. Google is your friend.
