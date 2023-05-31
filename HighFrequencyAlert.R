library(dplyr)
library(stringr)
library(RMySQL)
library(RODBC)
library(openxlsx)
library(tidyverse)
library(rio)
library(lubridate)
library(openxlsx)
options(scipen = 999)

#Establish Connections
connRVRX <- dbConnect(MySQL(),user='xxx',password='xxx',host='xxx.xxx.xx')
dbSendQuery(connRVRX,"Use xxx")
connMF2 <- dbConnect(MySQL(),user='xxxxx',password='xxx',host='xxxxxx')
dbSendQuery(connMF2,"Use rx")
dbconnection <- odbcDriverConnect("Driver=ODBC Driver 17 for SQL Server;Server=xxxxx; Database=xxxxx;Uid=xxxx; Pwd=xxxxx;")

PreviousNotification <- read.xlsx("//PreviousFlaggedItems.xlsx")
MVPItems <- dbGetQuery(connMF2, "SELECT ItemID FROM BackendRetailPrices WHERE mvpFlag = '1'")

#Get items from sales database, filter out wholesale customers
Sales <- sqlQuery(dbconnection, "SELECT ItemID, WhseID, ItemShortDesc, TranDate, QtyOrd FROM vdvSalesOrderLine
                                 WHERE CompanyID = 'HPC'
                                 AND CustID NOT LIKE '%00-%'
                                 AND CustID NOT LIKE '%21-%'
                                 AND ItemID NOT LIKE '%[^0-9]%'") %>%
  mutate("TranDate" = as.Date(substr(TranDate, 1,10)),
         "ItemID" = as.character(ItemID)
         ) %>%
  filter(TranDate >= Sys.Date()-14) %>% #Two week span
  group_by(ItemID, WhseID, TranDate) %>%
  mutate("SoldInDay" = sum(QtyOrd), #Sold in Day
         "OrdersInDay" = length(TranDate)
         ) %>%
  distinct(ItemID, WhseID, ItemShortDesc, TranDate, SoldInDay, OrdersInDay) %>%
  group_by(ItemID, WhseID) %>%
  mutate("AvgPerDayPastWeek" = ceiling(mean(SoldInDay[TranDate != Sys.Date()])),
         "StdPastWeek" = ceiling(sd(SoldInDay)),
         "StdOrdersPastWeek" = ceiling(sd(OrdersInDay)),
         "AvgPerDayOrdersPastWeek" = ceiling(mean(OrdersInDay[TranDate != Sys.Date()])),
         "SoldToday" = ifelse(Sys.Date() %in% TranDate, SoldInDay[TranDate == Sys.Date()], 0),
         "OrdersToday" = ifelse(Sys.Date() %in% TranDate, OrdersInDay[TranDate == Sys.Date()], 0),
         ) %>%
  ungroup() %>%
  filter(!ItemID %in% MVPItems$ItemID) %>% #Filter out MVP items
  filter((SoldToday > ceiling(AvgPerDayPastWeek+(StdPastWeek*0.75))) & (OrdersToday > AvgPerDayOrdersPastWeek+(StdOrdersPastWeek*0.75))) %>%
  left_join(dbGetQuery(connMF2, "SELECT DISTINCT ItemID, WhseID, SKUStockLevel AS StockLevel FROM InventoryInfo"), by = c("ItemID","WhseID")) %>% #Get stock levels
  distinct(ItemID, WhseID, ItemShortDesc, StockLevel, SoldToday, AvgPerDayPastWeek, AvgPerDayOrdersPastWeek, SoldToday, OrdersToday)

FrequencyExport <- Sales %>%
  filter(!ItemID %in% PreviousNotification$ItemID)
  
#If there are any flags, email the information to the needed people
  if(nrow(FrequencyExport) > 0){
    PrevFileName <- "//home//rvp//R//Pricing//PreviousFlaggedItems.xlsx"
    write.xlsx(Sales, PrevFileName)
    
    ExportFile <- "//home//rvp//R//Pricing//FreqIncreaseItems.xlsx"
    write.xlsx(FrequencyExport,ExportFile)
    
    cmd <- paste0("echo \" Items Detected to be selling quicker than usual.\n \n \n \n \n \n I am a robot. Beep Boop Beep. Please do not reply.\" | mutt -s \"Item Frequency Increase Detected\" -a \"",ExportFile,"\" -- kristianar@xxxxxx,xxxx@xxxxxx,xxxx@xxxxxx,xxxx@xxxxxx,xxxx@xxxx,xxxx@xxxx") 
    system(cmd) 
  }
  
  
  
