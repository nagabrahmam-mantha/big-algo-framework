# Notes on parms folder

## What goes here:

* I keep parameter files in json format in this folder.  This prevents hard coding usernames, passwords etc.  I also have account parameters for various tools.

* Example file report.json

* {"rptID":"123456", "token":"11507859573166978654321", rptname":"Activity_allDataYTD_xml", "outfolder":"output/flex/"}

* I have created a parms.json file that has 2 levels connect (with all the conntion info) and account (With all the account information including alias for the accounts).

* the account section will read in the available accounts, but also Alias names that are helpful on reports.  
* For example *"X1234678": "M-ROTH"* it may be hard to remember the account number, however M-ROTH would be much easier to recognize in the reports.

## Useage

file.py is used to read these json files.
dlFlexToMultiXL.py has a sample of how to call and use the report.json file

## Folder structure

* Keeping this folder structure as it is setup, will then allow you to put parameter files in the parm folder and output will be written to the output folder from any of the sample code and no sensitive data will be inadvertantly synced up to GitHub.
