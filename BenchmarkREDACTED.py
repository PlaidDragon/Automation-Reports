import json
import requests
import psycopg2
import pandas as pd
import gspread
import re
import numpy as np
from datetime import datetime
import time
from urllib.parse import parse_qs
pd.options.mode.chained_assignment = None  # default='warn'

gc = gspread.service_account(filename='xxx.json') # Google Sheets API auth

def lambda_handler(event, context):
    def pullBTMets(pageNameSynth=[], pageNameRum=[],
                   startDate=datetime.strftime(datetime.now(), '%Y-%m-%d'),
                   endDate=datetime.strftime(datetime.now(), '%Y-%m-%d'),
                   site="yyyyy", searchBy="pageName",
                   email='xxx@xxx.com', apiKey='xxxxxxxxxx'):
        dateDiff = datetime.strptime(endDate, '%Y-%m-%d') - datetime.strptime(startDate,'%Y-%m-%d')  # Define the number of days to check if it is less than 7
        # Define the groupBy parameter for the API call depending on user input
        if searchBy == "pageName":
            groupBy = ["pageName", "device", "time"]
        else:
            groupBy = ["url", "device", "time"]

        if ((dateDiff.days > 7) and (searchBy == 'urlSearch')) or (dateDiff.days > 30):
            dateList = pd.date_range(start=startDate, end=endDate, freq='w').strftime('%Y-%m-%d').tolist()
            dateList.append(endDate)
            dateList.insert(0, startDate)
            dateList = list(set(dateList))
            dateList.sort()
        else:
            dateList = [startDate, endDate]

        responseDFSynth = pd.DataFrame()
        responseDFRum = pd.DataFrame()
        for d in range(0, len(dateList) - 1):
            # Dates need to be converted to Epoch timestamps
            date0 = int((datetime.strptime(dateList[d], '%Y-%m-%d') - datetime(1970, 1, 1)).total_seconds())
            date1 = int((datetime.strptime(dateList[d+1], '%Y-%m-%d') - datetime(1970, 1, 1)).total_seconds()-1+(86400))


            # Pull RUM data if a RUM page was specified
            if len(pageNameRum) > 0:
                # Body creation for the Blue Triangle API call - RUM
                bodyRum = {"site": site, "start": date0, "end": date1, "dataType": "rum",
                           "dataColumns": ["pageHits","onload", "largestContentfulPaint", "totalBlockingTime", "cumulativeLayoutShift",
                                           "firstByte",
                                           "timeToInteractive", "firstContentfulPaint", "firstInputDelayDuration"],
                           "group": groupBy, "limit": 50000, searchBy: pageNameRum,
                           "avgType": "arithmetic", "bucketSize":"hour", "botTraffic": "excludeBots"}

                bodyRum = {"site": site, "start": date0, "end": date1, "dataType": "rum",
                           "dataColumns": ["pageHits", "onload", "largestContentfulPaint", "totalBlockingTime",
                     "cumulativeLayoutShift", "firstByte", "timeToInteractive",
                     "firstContentfulPaint", "firstInputDelayDuration"],
                           "group": ['pageName', 'device'], "limit": 50000, searchBy: pageNameRum,
                           "avgType": "percentile", "percentile": "75", "bucketSize": "hour", "botTraffic": "excludeBots"}


                responseRum = requests.post(url='https://api.bluetriangletech.com/performance',
                                            headers={
                                                'X-API-Email': email,
                                                'X-API-Key': apiKey
                                            },
                                            json=bodyRum
                                            )
                try:
                    responseDFRum0 = pd.json_normalize(responseRum.json(), 'data')  # Create dataframe from response json
                except:
                    responseDFRum0 = pd.DataFrame()

                if len(responseDFRum0) > 0:
                    # Typical cleaning of the columns, and converting ms to seconds
                    responseDFRum0 = responseDFRum0.iloc[
                        np.where((responseDFRum0["device"] == 'Mobile') | (responseDFRum0["device"] == 'Desktop'))]
                    responseDFRum0[["onload","largestContentfulPaint", "totalBlockingTime", "firstByte",
                                   "timeToInteractive", "firstContentfulPaint", "firstInputDelayDuration"]] = responseDFRum0[
                        ["onload", "largestContentfulPaint", "totalBlockingTime", "firstByte", "timeToInteractive",
                         "firstContentfulPaint",
                         "firstInputDelayDuration"]].apply(pd.to_numeric, errors='coerce').div(1000)
                responseDFRum = responseDFRum.append(responseDFRum0)

            if len(pageNameSynth) > 0:
                # Body creation for the Blue Triangle API call - Synthetic
                if searchBy == 'pageName':
                    groupBySynth = [groupBy[0]]
                    columnsQuant = [groupBy[0]]
                    columnsQuant.extend(
                        ["onload", "largestContentfulPaint", "totalBlockingTime", "cumulativeLayoutShift", "firstByte",
                         "timeToInteractive", "firstContentfulPaint", "speedIndex"])
                    columnsMean = [groupBy[0]]
                    columnsMean.extend(["pageSize", "imageBytes", "elementCount"])
                    bodyGroup = [n for n in groupBy if n != 'device']
                else:
                    groupBySynth = groupBy[0:2]
                    columnsQuant = groupBy[0:2]
                    columnsQuant.extend(["onload", "largestContentfulPaint", "totalBlockingTime", "cumulativeLayoutShift", "firstByte",
                                    "timeToInteractive", "firstContentfulPaint", "speedIndex"])
                    columnsMean = groupBy[0:2]
                    columnsMean.extend(["pageSize", "imageBytes", "elementCount"])
                    bodyGroup = groupBy


                bodySynth = {"site": site, "start": date0, "end": date1, "dataType": "synthetic",
                             "dataColumns": ["pageHits", "onload", "largestContentfulPaint", "totalBlockingTime", "cumulativeLayoutShift",
                                             "firstByte",
                                             "timeToInteractive", "firstContentfulPaint", "speedIndex", "pageSize",
                                             "imageBytes",
                                             "elementCount"],
                             "group": bodyGroup, "limit": 50000, searchBy: pageNameSynth,
                             "avgType": "arithmetic", "bucketSize": "hour", "botTraffic": "excludeBots"}
                # POST request to Blue Triangle API
                responseSynth = requests.post(url='https://api.bluetriangletech.com/performance',
                                              headers={
                                                  'X-API-Email': email,
                                                  'X-API-Key': apiKey
                                              },
                                              json=bodySynth
                                              )
                try:
                    responseDFSynth0 = pd.json_normalize(responseSynth.json(), 'data')  # Create dataframe from response json
                except:
                    responseDFSynth0 = pd.DataFrame()

                if len(responseDFSynth0) > 0:
                    responseDFSynth0[["onload", "largestContentfulPaint", "totalBlockingTime", "firstByte",
                                     "timeToInteractive", "firstContentfulPaint", "pageSize", "imageBytes", "speedIndex"]] = responseDFSynth0[[
                        "onload", "largestContentfulPaint", "totalBlockingTime", "firstByte",
                                         "timeToInteractive", "firstContentfulPaint", "pageSize", "imageBytes",
                                         "speedIndex"]].apply(pd.to_numeric, errors='coerce').div(1000)
                responseDFSynth = responseDFSynth.append(responseDFSynth0)

        if len(responseDFRum) > 0:
            responseDFRum0[["onload", "largestContentfulPaint", "totalBlockingTime",
                                            "cumulativeLayoutShift", "firstByte", "timeToInteractive",
                                            "firstContentfulPaint", "firstInputDelayDuration"]] = responseDFRum0[["onload", "largestContentfulPaint", "totalBlockingTime",
                                            "cumulativeLayoutShift", "firstByte", "timeToInteractive",
                                            "firstContentfulPaint", "firstInputDelayDuration"]].astype('float64')
            responseDFRum = responseDFRum0[[groupBy[0], "device", "onload", "largestContentfulPaint", "totalBlockingTime",
                                            "cumulativeLayoutShift", "firstByte", "timeToInteractive",
                                            "firstContentfulPaint", "firstInputDelayDuration"]].groupby(groupBy[0:2], as_index=False).quantile(0.75).fillna('-')
            hitsR = responseDFRum0[groupBy].copy()
            hitsR["pageHits"] = responseDFRum0["pageHits"].astype("int")
            hitsR = hitsR.groupby(groupBy[0:2], as_index=False).sum()
            responseDFRum = responseDFRum.merge(hitsR, on=groupBy[0:2], how="left")
            responseDFRum = responseDFRum[[groupBy[0], "device", "pageHits", "onload", "largestContentfulPaint", "totalBlockingTime",
                                            "cumulativeLayoutShift", "firstByte", "timeToInteractive",
                                            "firstContentfulPaint", "firstInputDelayDuration"]]

        if len(responseDFSynth) > 0:
            responseDFSynth[["cumulativeLayoutShift", "elementCount","pageHits"]] = responseDFSynth[["cumulativeLayoutShift", "elementCount","pageHits"]].apply(lambda x: x.astype('float64'))
            responseDFSynthQuants = responseDFSynth[columnsQuant].groupby(groupBySynth, as_index=False).quantile(0.75)
            responseDFSynthMeans = responseDFSynth[columnsMean].groupby(groupBySynth, as_index=False).mean()
            hits = responseDFSynth[groupBySynth].copy()
            hits["pageHits"] = responseDFSynth["pageHits"]
            hits = hits.groupby(groupBySynth, as_index=False).sum()
            responseDFSynth = responseDFSynthQuants
            responseDFSynth[responseDFSynthMeans.columns] = responseDFSynthMeans[responseDFSynthMeans.columns]
            responseDFSynth = responseDFSynth.merge(hits, on=groupBySynth, how="left")
            responseDFSynth = responseDFSynth.fillna('-')
            if searchBy == 'pageName':
                values = ['mobile', 'desktop']
                conditions = list(map(responseDFSynth['pageName'].str.lower().str.contains, values))
                responseDFSynth['device'] = np.select(conditions, values, 'Unspecified')
            columnsFin = [groupBySynth[0]]
            columnsFin.extend(["device","pageHits", "onload", "largestContentfulPaint", "totalBlockingTime",
                                "cumulativeLayoutShift", "firstByte", "timeToInteractive",
                                "firstContentfulPaint", "speedIndex", "pageSize", "imageBytes", "elementCount"])
            responseDFSynth = responseDFSynth[columnsFin].fillna('-')

        return [responseDFRum, responseDFSynth]




    try:
        req_body = event['body']
        params = parse_qs(req_body)
        print(req_body)  # Print these out for Cloudwatch Log debugging
        reqText = params['text'][
                      0] + ' test'  # add a word to the end of the text string so the regex works right. I know it's not perfect
        print(reqText)
        # Regex horror to get the needed parameters...
        fromDate0 = re.findall('fromDate.+?(\\d{4}\\-\\d{2}\\-\\d{2})', reqText)[0]
        toDate0 = re.findall('toDate.+?(\\d{4}\\-\\d{2}\\-\\d{2})', reqText)[0]

        pageNameSynth0 = re.findall('pageNameSynth.\((.*?)\)', reqText)
        if len(pageNameSynth0) > 0:
            pageNameSynth0 = pageNameSynth0[0].replace(", ", ",").split(",")
        pageNameRum0 = re.findall('pageNameRum.\((.*?)\)', reqText)
        if len(pageNameRum0) > 0:
            pageNameRum0 = pageNameRum0[0].replace(", ", ",").split(",")


        site0 = re.findall('site.(.*?)\ ', reqText)[0]
        searchBy0 = re.findall('searchBy.(.*?)\ ', reqText)[0]

        addText = ''  # empty string to fill later if errors are found

        sheetTitle_in = params['user_name'][0] + ' ' + 'COMPANY' + ' ' + fromDate0 + ' ' + toDate0  # Define Title of new sheet to create
        newSheet = gc.copy(file_id='SHEET_SKELETON',title=sheetTitle_in)  # create a new sheet
        workbook = gc.open_by_key(newSheet.id)  # open the newly created sheet
        synthBench = workbook.get_worksheet(0)  # define the worksheets in the workbook
        rumBench = workbook.get_worksheet(1)
        now = datetime.now()

        # Since you can only search by one url at a time, if the user wants multiple urls, we have to go through this mess of a loop
        if searchBy0 == "urlSearch" and ((len(pageNameSynth0) > 1) or (len(pageNameRum0) > 1)):

            rumDat = pd.DataFrame()  # Empty data frames to fill
            synthDat = pd.DataFrame()
            # Go through all the listed Synthetic data names
            if len(pageNameSynth0) > 0:
                for i in range(0, len(pageNameSynth0)):
                    btMetsSynth = pullBTMets(pageNameSynth=pageNameSynth0[i], pageNameRum=[],
                                             startDate=fromDate0, endDate=toDate0,
                                             site=site0, searchBy=searchBy0,
                                             email='xxx@xxx.com', apiKey='xxxxx')
                    if len(btMetsSynth[1]) == 0:  # Add a message explaining that data could not be found, as necessary
                        addText = addText + '\nI could not find Synthetic data for ' + pageNameSynth0[i] + '\n\n'
                    synthDat = synthDat.append(btMetsSynth[1])  # Fill the aformentioned dataframe

            # Go through all the listed RUM data names
            if len(pageNameRum0) > 0:
                for i in range(0, len(pageNameRum0)):
                    btMetsRum = pullBTMets(pageNameSynth=[], pageNameRum=pageNameRum0[i],
                                           startDate=fromDate0, endDate=toDate0,
                                           site=site0, searchBy=searchBy0,
                                           email='xxx@xxx.com', apiKey='xxxxx')
                    if len(btMetsRum[0]) == 0:  # Add a message explaining that data could not be found, as necessary
                        addText = addText + '\nI could not find RUM data for ' + pageNameRum0[i] + '\n\n'
                    rumDat = rumDat.append(btMetsRum[0])  # Fill the aformentioned dataframe

        # If urlsearch is not specified for more than one url, we can do a single API call
        else:
            btMets = pullBTMets(pageNameSynth=pageNameSynth0, pageNameRum=pageNameRum0,
                                startDate=fromDate0, endDate=toDate0,
                                site=site0, searchBy=searchBy0,
                                email='xxx@xxxx.com', apiKey='xxxxxxx')
            rumDat = btMets[0]
            synthDat = btMets[1]

            # Fill the data into the workbook as appropriate
        if len(rumDat) > 0:
            rumBench.update('A8:M200', rumDat.values.tolist(), value_input_option="USER_ENTERED")
            rumBench.update('A1', now.strftime("%Y-%d-%m %H:%M:%S"), value_input_option="USER_ENTERED")
            rumBench.update('A2', 'REAL USER DATA', value_input_option="USER_ENTERED")
        if len(synthDat) > 0:
            synthBench.update('A8:N200', synthDat.values.tolist(), value_input_option="USER_ENTERED")
            synthBench.update('A1', now.strftime("%Y-%d-%m %H:%M:%S"), value_input_option="USER_ENTERED")
            synthBench.update('A2', 'SYNTHETIC DATA', value_input_option="USER_ENTERED")

            # Victory message
        slackMessage = {'text': '<@' + params['user_id'][
            0] + '> ' + addText + 'I have completed your benchmark report request! Please see it <https://docs.google.com/spreadsheets/d/' + newSheet.id + '|here>\nHave a great day!'}
        resp = requests.post(params['response_url'][0], data=json.dumps(slackMessage),
                             headers={'Content-Type': 'application/json'})

    # If anything fails for some reason, alert the user that there was an error.
    except:
        slackMessage = {'text': '<@' + params['user_id'][
            0] + '> ' + addText + 'I encountered an error. The most likely reason for this is parameter miscomunication. Please use command `/Help` for more information on how to supply the correct parameters'}
        resp = requests.post(params['response_url'][0], data=json.dumps(slackMessage),
                             headers={'Content-Type': 'application/json'})

    return {
        'statusCode': resp.status_code,
        'body': resp.text
        # 'id': newSheet.id
        }

