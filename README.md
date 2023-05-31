# Automation-Reports
Automated report scripts and their output

# Table of contents
1. [Opti-Bot](#optiBot)
2. [Global Tracker](#globalTracker)
3. [Unusual Selling Frequency Alert](#freqAlert)
4. [T3 Generator](#T3)


## **Opti-Bot:**<a name="optiBot"></a>

**Files included:** BenchmarkREDACTED.py

**Purpose:** SEO engineers require speed performance numbers for the pages of the site that they are auditing. This involves submitting a ticket, an analyst picking up the ticket, and running the required report which is often similar to previous requests. The idea was to not only create a universal reporting layout, but give the engineers the ability to call a bot to create their needed report on demand with little to no involvement from the analysts. The result became Opti-bot; a series of Python scripts hosted on AWS that hook into the company's Slack channel.

Opti-Bot uses a skeleton Google Sheet that it copies and writes to using information from the given monitoring tool's API. The largest challenge here was how to limit the work and inputs required from the engineer during the request, given that the company has multiple clients who all use a differnt monitoring tool (and thus differnt APIs). The work around was to create a dictionary of our clients by using their respective Slack channel id, mapping those IDs to a seperate ID that correlates to a specific monitoring tool. The API that is used is dependant on the Slack channel ID that the request comes through. 

Opti-Bot is constantly growing and evolving. It has specifically been set up to be as maliable as possible since the company is constantly changing its client-base and therefore the tooling Opti-Bot generates reports from is constantly changing. The success of Opti-Bot is measurable: The time it takes to report on the performance KPIs of a given webpage has been reduced by ~30 mins for each ticket. It only takes <5 minutes to impliment a new client who is using an existing monitoring tool. On top of this, new analysts are able to utilize Opti-Bot rather than learning the API useage of each and every tool which also limits the number of potential reporting mistakes and discontinuities.

There are several types of reports that Opti-Bot has been included to give including: 
* Report of all synthetic monitors currently monitoring the site, along with their specifications
* Speed Metrics for a specified timeframe for a specified page/groups of pages
* Speed metrics for a specific page compared over two date ranges
* Generate a Crux report using Google's Crux API

personal note: Opti-Bot uses many scripts that are hosted in AWS. Included in this repository is only a sample of one.


**Libraries used:** json, requests, pandas, numpy, gspread, re, urllib

**Output:** 

![image](https://github.com/PlaidDragon/Automation-Reports/assets/135033377/8463e823-4b7f-44ac-957c-eb4bbd72ee44)
![image](https://github.com/PlaidDragon/Automation-Reports/assets/135033377/b88d3217-109d-4414-84e3-0dd72c9f3359)




## **AB Testing Global Tracker:**<a name="globalTracker"></a>

**Files included:** GlobalTracker_Jira.py, GlobalTracker_Optimizely.py

**Purpose:** The Estee Lauder Companies are made up of dozens of smaller companies. As the lead analyst in their global AB testing project, I had to keep track of all tests and their results. Our Project Manager also had to figure out how to prioritize each prosposed test. The solution was to create a spreadsheet of all AB testing tickets, their information and status, and connect this data to a Gnatt tracker as well as a summary of all their results. This was acomplished useing Jira's API, Google Sheet's API, and Optimizely's API. 

Using the data from Jira, I developed a normalized prioritization score that depended on the primary metric, estimated traffic impacted, estimated effect the change would have, and how close the launch date of the test was. This allowed the brand managers and the project managers to have a clear sight on what tests should be given priority.

Involving informaion from Jira was straightforward. Automating results from Optimizely, even high-level results, was more of a challenge. The script had to be able to catch teh differnce between A/B tests, A/A tests, MVT tests, and A/B/N tests. The script also could not overwhelm Optimizely's API or the limit on Google Sheet's API (60 requests per minute). This was a challege considering the number of tests each brand was running. The result was two Python scripts: One for pulling in all the relaveant Jira information and another for pulling in Optimizely results and attaching it to the relavant Jira ticket.

The one that summarizes Optimizely's data has many error catches and if/then statements in its attempt to correctly summarize every type of test. There are limits; considering there is no official way to connect a Jira ticket to an Optimizely test, if there is no internal numbering system (or if there is an error in a tickets internal numbering system) the script will not be able to find the appropriate test in Optimizely. Optimizely's API also gets overloaded quickly so the script much sleep often and therefore takes some time to run. 

There are also many issues in Jira that will be carried over to the global tracker. For instance, many stakeholders put "Site Conversion Rate" as their proposed primary metric when setting up the ticket, even when this is most likely not the best descriptor for the success of the test. These issues will be carried over until an analyst looks over and corrects the ticket.

personal note: This script is designed to be ran on a server like a cronjob on an AWS EC2 server. This script is very dependant on the way our testing sytem was set up. 


**Libraries used:** numpy, pandas, requests, gspread, re, atlassian, json

**Output:** 
![image](https://github.com/PlaidDragon/Automation-Reports/assets/135033377/47327e7e-02b7-4935-908d-bcdbb07f87fb)




## **High Frequency Alert:**<a name="freqAlert"></a>

**Files included:** 

**Purpose:** The small pharmaceutical distribution company often found itself a step behind other larger companies regarding large changes in stock of the industry. While news scrapers did as much as they could, the most effective method of ensuring limits were placed on items sold per order when runs on the market happened, was to monitor the selling frequency of each item each day. This script was designed to do as much. An R file meant to be hosted on Linux and attached to a cronjob, it monitors the amount that each item has moved through the day. If it detects an item selling more than the average +- 75% of the standard deviation over two weeks, it creates a spreadsheet that it emails out to the necessary people to look into. 



**Libraries used:** dplyr, stringr, RMySQL, RODBC, tidyverse, lubridate, openxlsx

**Output:** 

![image](https://github.com/PlaidDragon/Automation-Reports/assets/135033377/88576e0a-7c0c-430e-a03e-ac81999b956f)


## **T3 Builder (Internal Pedigree Script):**<a name="T3"></a>

**Files included:** GenerateT3.py (Database caller not included here)

**Purpose:** Pharmaceutical manufacturers and distributors must keep a specific paper trail of every shipment and receaval of prescription drugs. Most companies opt to use a third party vendor to create these paper trails (See [GUIS - MATTI](#https://github.com/PlaidDragon/Dashboards-GUIs#matti)). For a small distributing company, this means paying tens of thousands of dollars to a third party vendor, not including the man-power required to input the data to the vendor. My proposed solution was a python script that connected to the company's internal database and used the 'tried and true' data within to create T3s without the use of a third party vendor

personal note: I left this company before I was able to impliment this, although I did leave them with the necessary scripts. I am unsure if they moved forward with this proposal and therefore do not know the extent of its success.


**Libraries used:** fpdf, sqllalchemy, mysql, pandas, dfply, pyodbc

**Output:** 

![image](https://github.com/PlaidDragon/Automation-Reports/assets/135033377/5fa5258d-a8d4-40b7-aaaa-ae93d640fa72)
