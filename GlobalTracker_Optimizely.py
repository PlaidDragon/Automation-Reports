import datetime, time

import numpy as np
import requests, pandas as pd, gspread, re
gc = gspread.service_account(filename='xxxxx.json')
urlBase = "https://api.optimizely.com"
#APIKey
apiKey = "Bearer 2:xxxxx"

#-----Fetch list of running/completed experiments in sheet-----
tracker = gc.open_by_key('xxxxxxx')
prioritizerSheet = tracker.get_worksheet(1)
prioritizerData = pd.DataFrame(prioritizerSheet.get())
prioritizerData = prioritizerData[prioritizerData[0] != '']
prioritizerData.columns = prioritizerData.iloc[0]
prioritizerData.drop(prioritizerData.index[0], inplace=True)
prioritizerData.rename(columns={'TST Number':'tstID'}, inplace=True)

def getID(string):
    try:
        s = re.findall("TST[^|]*", string)[0]
        s = s.replace(" ", "")
    except:
        s = None
    return s

# prioritizerData['tstID'] = prioritizerData.Description.apply(getID)
# prioritizerData.tstID.replace(" ", "", inplace=True)


#--------List Projects-----------
projectsReq = requests.get(url=urlBase + "/v2/projects?per_page=100",
                              headers={
                                  'Authorization': apiKey,
                                  'Content-Type': 'application/json'
                              }
                              )
#if projectsResp > 100, need to include a second page call here
projectsResp = pd.json_normalize(projectsReq.json())

#filterDF = projectsResp[projectsResp['name'].str.contains('MAC')]
filterDF = projectsResp.copy()
#----------List experiments in each project--------------
experimentsMetaDF = pd.DataFrame()
for id in filterDF.id:
    experimentsReq = requests.get(url=urlBase + "/v2/experiments?project_id=" + str(id) + "&per_page=100",
                               headers={
                                   'Authorization': apiKey,
                                   'Content-Type': 'application/json'
                               }
                               )
    experimentsResp = pd.json_normalize(experimentsReq.json())
    experimentsMetaDF = pd.concat([experimentsMetaDF, experimentsResp])

experimentsMetaDF['tstID'] = experimentsMetaDF.name.apply(getID)
experimentsMetaDF.tstID.replace(" ", "", inplace=True)
experimentsMetaDF.dropna(subset=['tstID'], inplace=True)

#----Get Statuses for Prioritizer----
prioritizerStatus = experimentsMetaDF[['tstID','status']]
sortPrioritizer = prioritizerData[['tstID','Status','Ended']].copy()
# sortPrioritizer = sortPrioritizer[sortPrioritizer.Ended == 'FALSE']
sortPrioritizer[sortPrioritizer.Status == "Cancelled"]
sortPrioritizer['sortIndex'] = sortPrioritizer.index
prioritizerStatus = pd.merge(prioritizerStatus, sortPrioritizer, on='tstID', how='right')
prioritizerStatus.loc[prioritizerStatus["Status"] == "Cancelled", ["status"]] = "paused"
prioritizerStatus.sortIndex = prioritizerStatus.sortIndex + 1
prioritizerStatus.status.fillna('not_started', inplace=True)
prioritizerStatus = prioritizerStatus[(prioritizerStatus.tstID != '')]
prioritizerStatus = prioritizerStatus[(prioritizerStatus.tstID != 'TST:XXX')]
#prioritizerStatus.index = prioritizerStatus.sortIndex.values.tolist()

for i in range(0, len(prioritizerStatus)):
    if prioritizerStatus.status.iloc[i] == 'running':
        running = 'True'
        ended = 'False'
    elif prioritizerStatus.status.iloc[i] == 'paused':
        running = 'False'
        ended = 'True'
    else:
        running = 'False'
        ended = 'False'
    writeStringP = 'AD' + str(prioritizerStatus.sortIndex.iloc[i]) + ':AE' + str(prioritizerStatus.sortIndex.iloc[i])
    prioritizerSheet.update(writeStringP, [[running, ended]], value_input_option="USER_ENTERED")
    if i % 60 == 0:
        time.sleep(60)
    # print(i)
    # print(writeStringP)
    # print(running, ended)
#--------------------------------------

#------------Get Now Updated Data from Sheet------------
allEnded = tracker.get_worksheet(5)
allEnded = pd.DataFrame(allEnded.get())
allEnded.columns = allEnded.iloc[0]
allEnded.drop(allEnded.index[0], inplace=True)
allEnded['tstID'] = allEnded['TST Number']
allEnded = allEnded[allEnded.Status != "Cancelled"] #filter out cancelled experiments
allEnded.drop(['Status'], axis=1, inplace=True)
resultsTracker = tracker.get_worksheet(4)
enteredData = pd.DataFrame(resultsTracker.get()) #Identify data that is already in the sheet
enteredData.columns = enteredData.iloc[0]
enteredData.drop(enteredData.index[0], inplace=True)
enteredData['Jira Ticket Number'] = enteredData['Jira Ticket Number'] .replace('', None)
enteredData = enteredData[~enteredData['Jira Ticket Number'].isnull()].copy() #Filter out experiments with no identifiable tst number
enteredData['tstID'] = enteredData['TST Number']
notIncluded = allEnded[~allEnded['tstID'].isin(enteredData['tstID'])].dropna() #Identify tests not on the results sheet
tstIDs = enteredData.tstID
enteredData = enteredData[enteredData.columns[20:]].copy()
enteredData['tstID'] = tstIDs
enteredData['Ended'] = enteredData['Ended'] .replace('', None)
enteredData.reset_index(drop=True, inplace=True)
runningData = enteredData[enteredData['Ended'].isnull()] #Get data that is running currently
if len(runningData) == 0:
    updateResults = notIncluded['tstID']
else:
    updateResults = pd.concat([runningData['tstID'], notIncluded['tstID']])
#----------------------------------------------

experimentsMetaDF = experimentsMetaDF[experimentsMetaDF.tstID.isin(updateResults)]
groupedMeta = experimentsMetaDF.groupby(by=['tstID'])
experimentsMetaDF = groupedMeta.apply(lambda g: g[g.index == g.index.min()])

experimentsMetaDF.index = experimentsMetaDF.id



#------Experiment Data--------
writeDF = pd.DataFrame()
for id in experimentsMetaDF.id:
    time.sleep(0.5)
    try:
        experimentResResp = requests.get(url=urlBase + "/v2/experiments/" + str(id) + "/results" ,
                                         headers={
                                             'Authorization': apiKey,
                                             'Content-Type': 'application/json'
                                         }
                                         )
        resultsResp = experimentResResp.json()['metrics']
        results = pd.json_normalize(resultsResp)
        #Users Calculations
        usersCols = [col for col in results.columns if 'samples' in col]
        results[usersCols].iloc[0].sum()
        if experimentsMetaDF.status.loc[id] == 'running':
            perDay = datetime.datetime.today()
            endedDate = ''
            dueDate = ''
        else:
            perDay = datetime.datetime.strptime(experimentsMetaDF.latest.loc[id][0:10], "%Y-%m-%d")
            endedDate = perDay
            dueDate = endedDate + datetime.timedelta(days=7)
        daysRan = (perDay - datetime.datetime.strptime(experimentsMetaDF.loc[id].earliest[0:10], "%Y-%m-%d")).days
        if daysRan < 1:
            daysRan = daysRan+2
        usersPerDay = round(results[usersCols].iloc[0].sum()/(daysRan-1),0)


        #Significance Calculation
        visitorsLeftCol = [col for col in results.columns if 'visitors_remaining' in col]
        if len(visitorsLeftCol) < 1:
            trafficStatus = "NA"
        else:
            usersNeeded = results[visitorsLeftCol].iloc[0][0]
            if round(usersNeeded/usersPerDay,0) > 40:
                trafficStatus = 'Will not Resolve'
            elif round(usersNeeded/usersPerDay,0) < 10:
                trafficStatus = 'Will Resolve'
            else:
                trafficStatus = 'May Resolve'

        #Winner Calculations
        sigCol = [col for col in results.columns if 'is_significant' in col]
        directionCol = [col for col in results.columns if 'lift_status' in col]

       #Status Determination
        if experimentsMetaDF.status.loc[id] == 'running':
            running = 'True'
        else:
            running = 'False'

        if running == 'True':
            winner = 'In Progress'

        #Winner Calculation
        if len(sigCol) < 1 and len(directionCol) < 1:
            winner = "NA"
        else:
            if results[sigCol].iloc[0][0] == True:
                if results[directionCol].iloc[0][0] == 'worse':
                    winner = 'Original'
                else:
                    winner = 'Variant'
            else:
                if results[directionCol].iloc[0][0] == 'worse':
                    winner = 'Inconclusive (Directional Decline)'
                elif results[directionCol].iloc[0][0] == 'better':
                    winner = 'Inconclusive (Directional Increase)'
                else:
                    winner = 'Inconclusive'

        #Results Concatination
        ciCols = [col for col in results.columns if 'confidence' in col]
        name = results.name.iloc[0]

        if len(ciCols) < 1:
            ciCols = [col for col in results.columns if 'rate' in col]
            rate = results[ciCols].iloc[0][0] * 100
            resultString = str(round(rate, 2)) + '% baseline to ' + name
        else:
            try:
                lower = results[ciCols].iloc[0][0][0]*100
                upper = results[ciCols].iloc[0][0][1]*100
                name = results.name.iloc[0]
                convClean = str.find(name, 'Checkout Confirmation')
                if convClean > 0:
                    name = 'Ecommerce Conversion Rate'
                resultString = str(round(lower,2)) + '% to ' + str(round(upper,2)) + '% effect to ' + name
            except:
                resultString = 'Unavailable'

        #Revenue Calculation
        revenueIndex = results[results.name.str.contains('Revenue')]
        sigCol = [col for col in results.columns if 'significant' in col]
        if len(revenueIndex)  == 0 or revenueIndex[sigCol].iloc[0][0] == False:
            revenueImpactSeen = 'False'
            revenueImpact = '-'
        else:
            revenueImpactSeen = 'True'
            lower = results[ciCols].iloc[revenueIndex.index[0]][0][0] * 100
            upper = results[ciCols].iloc[revenueIndex.index[0]][0][1] * 100
            revenueImpact = str(round(lower, 2)) + '% to ' + str(round(upper, 2)) + '%'

        trackerDict = {'tstID': experimentsMetaDF.tstID.loc[id],
                       'Running': running,
                       'Launched': experimentsMetaDF.loc[id].earliest[0:10],
                       'Users': float(results[usersCols].iloc[0].sum()),
                       'UsersPerDay': usersPerDay,
                       'UsersNeeded': float(usersNeeded),
                       'DaysUntilSig': round(usersNeeded / usersPerDay, 0),
                       'TrafficStatus': trafficStatus,
                       'TrafficStatusAsOf': datetime.datetime.today().strftime('%Y-%m-%d'),
                       'Ended': str(endedDate)[0:10],
                       'ResultsDueDate': str(dueDate)[0:10],
                       'Winner': winner,
                       'Results': resultString,
                       # 'ImpactPredicted': '',
                       'RevenueImpactSeen': revenueImpactSeen,
                       'RevenueImpact': revenueImpact
                       }

        trackerDF = pd.DataFrame(trackerDict, index=[0])
        writeDF = pd.concat([writeDF,trackerDF])
    except:
        print(id)
        continue
print('done')
#--------Write to SpreadSheet--------------


sortDF = pd.DataFrame({'tstID':enteredData.tstID})
sortDF['writeIndex'] = range(0, (len(enteredData)))

writeNew = writeDF[~writeDF.tstID.isin(sortDF.tstID)].copy()
indexList = range(len(enteredData), len(enteredData) + len(writeNew))
writeNew['writeIndex'] = indexList
writeDF = pd.merge(writeDF, sortDF, on='tstID')
writeDF = pd.concat([writeDF, writeNew])
tstIDs = writeDF.tstID.copy()
tstIDs.reset_index(inplace=True, drop=True)
writeDF.index = writeDF.writeIndex
writeDF.drop(['tstID','writeIndex'], axis=1, inplace=True)

#-------WRITE"------
writeDF1 = writeDF[writeDF.columns[0:12]]
writeDF2 = writeDF[writeDF.columns[12:14]]
ii = 0
time.sleep(60)
for i in writeDF.index:
    writeString0 = 'B' + str(i+2)
    writeString1 = 'U' + str(i+2) + ':AF' + str(i+2)
    writeString2 = 'AH' + str(i+2) + ':AI' + str(i+2)
    resultsTracker.update(writeString0, [[tstIDs.iloc[ii]]], value_input_option="USER_ENTERED")
    resultsTracker.update(writeString1, [writeDF1.loc[i].values.tolist()], value_input_option="USER_ENTERED")
    resultsTracker.update(writeString2, [writeDF2.loc[i].values.tolist()], value_input_option="USER_ENTERED")
    # print(tstIDs.iloc[ii])
    # print(writeString1)
    if ii % 19 == 0:
        time.sleep(60)
    ii += 1
print("Done")
