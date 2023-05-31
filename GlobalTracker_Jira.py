import pandas as pd, numpy as np, json, gspread, re
from atlassian import Jira
pd.options.mode.chained_assignment = None  # default='warn'
gc = gspread.service_account(filename='xxxxx.json')

jira = Jira(
    url='https://jira.xxxxx.com',
    token="xxxxxxx"
)
project = "EXPERIMENT"
resp = jira.get_project(project)

t = pd.json_normalize(resp)


#Get fields from Jira
ticketNum = jira.get_project_issues_count(project)
issue = jira.get_all_project_issues(project, fields='issuetype, customfield_30506,customfield_13501,customfield_17804,customfield_11513,customfield_30502,customfield_30900,reporter,status,customfield_11601,customfield_14602,customfield_31100,key,summary,customfield_30508', start=0, limit=ticketNum) #*all
#issueTest = jira.get_all_project_issues(project, fields='*all', start=0, limit=ticketNum) #*all
#issueDFTest = pd.DataFrame(issueTest)
#fieldsDFTest = pd.DataFrame(issueDFTest['fields'])
#fieldsDFTest = fieldsDFTest.fields.apply(pd.Series)

#Create Dataframes of ticket and issues
issueDF = pd.DataFrame(issue)
fieldsDF = pd.DataFrame(issueDF['fields'])
fieldsDF = fieldsDF.fields.apply(pd.Series)

#Filter out epics, focus only on issues
issueType = [d.get('name') for d in fieldsDF.issuetype]
epicInds = np.array(issueType)
epicInds = np.where(epicInds == 'Epic')[0]
fieldsDF = fieldsDF.iloc[epicInds]
issueDF = issueDF.iloc[epicInds]
fieldsDF.reset_index(inplace=True, drop=True)
issueDF.reset_index(inplace=True, drop=True)

#Account for tickets with missing information
for i in range(0,len(fieldsDF)):
    if fieldsDF.customfield_30900.iloc[i] is None:
        fieldsDF.customfield_30900.iloc[i] = {'displayName':''}

    if fieldsDF.customfield_14602[i] is None:
        fieldsDF.customfield_14602[i] = ''

    if not fieldsDF.customfield_31100[i] > 0:
        fieldsDF.customfield_31100[i] = {'estimatedDuration': ''}

#Extract data from the json for each field
primaries = [d.get('value') for d in fieldsDF.customfield_30506]
brands = [d[0].get('value') for d in fieldsDF.customfield_13501]
locales = [d[0].get('value') for d in fieldsDF.customfield_17804]
regions = [d[0].get('value') for d in fieldsDF.customfield_11513]
bexLead = [d.get('displayName') for d in fieldsDF.customfield_30502]
brandLead = [d.get('displayName') for d in fieldsDF.customfield_30900]
capLead = [d.get('displayName') for d in fieldsDF.reporter]
status = [d.get('name') for d in fieldsDF.status]
siteSection = [d.get('value') for d in fieldsDF.customfield_11601]
launchDate = [d[0:10] for d in fieldsDF.customfield_14602]
estimatedDuration = [d for d in fieldsDF.customfield_31100]


fieldsDF.fillna('', inplace=True)

#Create holder Dataframe
writeDict = {'ticket':issueDF.key,
             'tstID': '',
             'description': fieldsDF.summary,
             'size':'Medium',
             'status':status,
             'brand':brands,
             'locale':locales,
             'region':regions,
             'globalSponser':bexLead,
             'brandPM':brandLead,
             'capabilityLead': capLead,
             'siteSection':siteSection,
             'type':'',
             'primaryMetric':primaries,
             'predictedImpact': 0.02,
             'dailyTraffic': fieldsDF.customfield_30508,
             'estimatedTimeline':estimatedDuration,
             'devEffort':'Medium',
             'plannedLaunchDate':launchDate
             }
writeDF = pd.DataFrame(writeDict)

#Clean up the ticket Description
def getDesc(descListIn):
    descList = descListIn.upper()
    descList = descList.split("|")
    descClean = None
    for m in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC', "TBC"]:
        ind = [idx for idx, s in enumerate(descList) if m in s and len(s) < 11]
        if len(ind) > 0:
            descClean = descList[ind[0] - 1]
            break
        else:
            continue
    if descClean is None:
        descClean = descListIn
    return descClean

def getID(string):
    try:
        s = re.findall("TST[^|]*", string)[0]
        s = s.replace(" ", "")
    except:
        s = None
    return s

 #Get existing data from sheet
descCleaned = writeDF.description.apply(getDesc)
tstID = writeDF.description.apply(getID)
writeDF.description = list(descCleaned)
writeDF.tstID = list(tstID)
writeDF.ticket = '=HYPERLINK("https://jira.esteeonline.com/browse/' + writeDF.ticket + '", ' + '"' + writeDF.ticket + '")'
writeDF.replace(np.nan, '', inplace=True)
tracker = gc.open_by_key('1Jby1Fm4jp9dwL4HZ7m_VLlMhwecwMWRcv5Ynk9Qz-Es')
prioritizer = tracker.get_worksheet(1)
prioritizer.clear_basic_filter()
enteredData = pd.DataFrame(prioritizer.get())
enteredData = enteredData[enteredData[0] != '']

enteredData.columns = enteredData.iloc[0]
enteredData.drop(enteredData.index[0], inplace=True)
# enteredData.reset_index(inplace=True, drop=True)
# descCleaned = enteredData.Description.apply(getDesc)
# enderedTstID = enteredData.Description.apply(getID)
# enteredData['TST Number'] = list(enderedTstID)
# enteredData.Description = list(descCleaned)
enteredData['Jira Ticket Number'] = '=HYPERLINK("https://jira.esteeonline.com/browse/' + enteredData['Jira Ticket Number'] + '", ' + '"' + enteredData['Jira Ticket Number'] + '")'

#Ensure we do not overwrite the existing data, and keep the current sorting in the sheet
updateData = writeDF[writeDF['ticket'].isin(enteredData['Jira Ticket Number'])]
sortDF = pd.DataFrame({'ticket':enteredData['Jira Ticket Number']})
sortDF['index'] = range(0, (len(enteredData)))

existingData = pd.merge(updateData, sortDF, on='ticket')
existingData.sort_values('index', inplace=True)
existingData.drop('index', axis=1, inplace=True)

filteredWriteDF = writeDF[~writeDF['ticket'].isin(enteredData['Jira Ticket Number'])]
#filteredWriteDF = filteredWriteDF[filteredWriteDF.brand == "MAC"]

combinedDF = pd.concat([existingData, filteredWriteDF])
combinedDF.reset_index(inplace=True)
combinedDF.drop('index', axis=1, inplace=True)
writeString = 'A2' + ':S' + str(len(combinedDF)+1)
prioritizer.update(writeString, combinedDF.values.tolist(), value_input_option="USER_ENTERED")
prioritizer.set_basic_filter("A1:AE" + str(len(combinedDF)+1))
