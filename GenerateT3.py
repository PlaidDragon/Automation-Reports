from fpdf import FPDF
from DatabaseFunctions import * #Self-made Python script containing functions to collect needed data

pdf = FPDF(orientation='L', unit='mm', format='A4')
pdf.add_page('O')
# header(pdf)

class GenerateT3(FPDF):

     def __init__(self, itemData):
         self.pdf = FPDF(orientation='L', unit='mm', format='A4')
         self.pdf.add_page()
         self.itemData = itemData
         self.startHeader = 5
         self.startItemInfo = self.startHeader + 3

     def header(self):
         self.pdf.set_font("Arial", size=8)
         self.pdf.multi_cell(w=75, h=4, align='L',txt="Real Valuve Products Corp \n5100 CommerceWay\nSan Antonio, Tx 78218\nTel: 855-767-6655     Fax: 210-979-3398\nLicence: 1002541      Exp: 4/30/2020")
         self.pdf.set_font("Arial", 'B', size=12)
         self.pdf.cell(w=125, h=25, txt="REAL VALUE PRODUCTS T3 TEST", ln=0, align="C")
         self.pdf.image(r'C:\Users\kreedrvp\Documents\rvrx-web-logo.png', x=220, y=5, w=70, h=20)
         self.pdf.line(10, 30, 300, 30)
         self.pdf.output("test.pdf")


     def TransactionInformation(self):
         self.pdf.cell(w=0, h=25, ln=1)
         self.pdf.set_font("Arial", 'B', size=10)
         self.pdf.set_fill_color(213, 213, 213)
         self.pdf.cell(0, 7, txt="Transaction Information And Transaction Statement", align="L", ln=1, fill=1)
         self.pdf.cell(w=0, h=5, ln=1)
         self.pdf.set_font("Arial", 'B', size=8)

         self.mediItemInformation()
         self.tranItemInformation()

     def mediItemInformation(self):
         ndc = itemData["ItemID"]
         ndc = ndc[2:7]+'-'+ndc[7:11]+'-'+ndc[11:13]
         mediInfo = pullMediInfo(ndc).iloc[0]
         self.pdf.multi_cell(w=25, h=5, txt="  Manufacturer:\n  Dosage Form:")
         self.pdf.set_font("Arial", size=8)
         self.pdf.multi_cell(w=75, h=5, txt="{}\n{}".format(mediInfo["mfr"], mediInfo["dosage_form"]))

         self.pdf.set_font("Arial", 'B', size=8)
         self.pdf.multi_cell(w=25, h=5, txt="  Drug Name:\n  Container Size:")
         self.pdf.set_font("Arial", size=8)
         self.pdf.multi_cell(w=100, h=5, txt="{}\n{}".format(mediInfo["full_description"], mediInfo["size"]))

         self.pdf.set_font("Arial", 'B', size=8)
         self.pdf.multi_cell(w=20, h=5, txt="  NDC:\n  Strength:")
         self.pdf.set_font("Arial", size=8)
         self.pdf.multi_cell(w=0, h=5, txt="{}\n{} {}".format(mediInfo["ndc_dash"], mediInfo["strength"],mediInfo["strength_unit_of_measure"]))


     def cleanAddrs(self):
         itemShipToAddress = list([self.itemData["AddrLine1"], self.itemData["AddrLine2"], self.itemData["AddrLine3"],
                                   (self.itemData["AddrCity"] + ", " + self.itemData["AddrState"] + ", " + self.itemData["ShipToZip"]),
                                   self.itemData["AddrCountry"]])
         self.shipToAddress = [entry for entry in itemShipToAddress if entry]

         itemBillToAddress = list([self.itemData["BillAddrLine1"], self.itemData["BillAddrLine2"], self.itemData["BillAddrLine3"],
                                   (self.itemData["BillAddrCity"] + ", " + self.itemData["BillAddrState"] + ", " + self.itemData[
                                       "BillToZip"]),
                                   self.itemData["BillAddrCountry"]])
         self.billToAddress = [entry for entry in itemBillToAddress if entry]

         poData = pullShipFromAddr(self.itemData["PurchaseOrder"]).iloc[0]
         poAddressList = list([poData["AddrLine1"], poData["AddrLine2"], poData["AddrLine3"],
                               (poData["City"] + ", " + poData["State"] + ", " + poData["Zip"]),
                               poData["Country"]])
         self.poAddress = [entry for entry in poAddressList if entry]

     def tranItemInformation(self):
         self.pdf.line(x1=20, y1=60, x2=275, y2=60)
         self.pdf.cell(w=0, h=14, ln=1)
         self.pdf.set_font("Arial", 'B', size=8)
         self.pdf.cell(w=150, h=5,txt="                                               Lot Number                       Expiration                            Qty                          Transaction Number                              Transaction Date                           Customer PO")
         self.pdf.cell(w=0, h=5, ln=1)
         self.pdf.set_font("Arial", size=8)
         self.pdf.cell(w=20, h=5,
                  txt="                                                  {}                            {}                          {}                         {}                                        {}".format(
                      self.itemData["LotNo"], str(self.itemData["ExpirationDate"])[0:10], self.itemData["QtyShipped"],
                      self.itemData["SalesOrder"], str(self.itemData["ShipDate"])[0:10]))

     def tranHistory(self):
         self.pdf.cell(1, 10, ln=1)
         self.pdf.set_font("Arial", 'B', size=10)
         self.pdf.set_fill_color(213, 213, 213)
         self.pdf.cell(0, 8, txt="Transaction History",align="L", ln=1, fill=1)
         self.cleanAddrs()
         self.hopOne()
         self.hopTwo()
         self.addStatement()

     def hopOne(self):
         self.pdf.multi_cell(w=30, h=5, txt="Transaction Date: \nShipped Date: \n\n    Seller\n\n\n    Shipped\n    From:")
         self.pdf.set_font("Arial", size=6)
         self.pdf.multi_cell(w=50, h=5, txt="{}\n{}\n{}\n{}\n{}\n\n{}\n{}\n{}".format(str(self.itemData["ReceivedDate"])[0:10],
                                                                                 self.poData["VendShipDate"],
                                                                                 self.itemData["VendName"],
                                                                                 '\n'.join(self.poAddress),
                                                                                 self.itemData["VendName"], self.poAddress[0],
                                                                                 self.poAddress[1]))
         self.pdf.set_font("Arial", 'B', size=6)
         self.pdf.multi_cell(w=25, h=5, txt="Purchase Order: \n\n\n    Buyer\n\n\n    Shipped\n    To:")
         self.pdf.set_font("Arial", size=6)
         self.pdf.multi_cell(w=0, h=5,
                        txt="{}\n\n    REAL VALUE PRODUCTS\n    5100 COMMERCE WAY\n    SAN ANTONIO, TEXAS 78218\n\n    REAL VALUE PRODUCTS\n    5100 COMMERCE WAY\n    SAN ANTONIO, TEXAS 78218".format(
                            self.itemData["PurchaseOrder"]))
         self.pdf.rect(10, 79, 185, 55)

     def hopTwo(self):
         self.pdf.cell(0, 55, ln=1)
         self.pdf.set_font("Arial", 'B', size=6)
         self.pdf.multi_cell(w=30, h=5, txt="Transaction Date: \nShipped Date: \n\n    Seller\n\n\n\n    Shipped\n    From:")
         self.pdf.set_font("Arial", size=6)
         self.pdf.multi_cell(w=50, h=5,
                        txt="{}\n{}\nREAL VALUE PRODUCTS\n5100 COMMERCE WAY\nSAN ANTONIO, TEXAS 78218\n\nREAL VALUE PRODUCTS\n5100 COMMERCE WAY\nSAN ANTONIO, TEXAS 78218".format(
                            str(self.itemData["ShipDate"])[0:10], str(self.itemData["ShipDate"])[0:10]))
         self.pdf.set_font("Arial", 'B', size=6)
         self.pdf.multi_cell(w=25, h=5, txt="Sales Order: \n\n\n    Buyer\n\n\n    Shipped\n    To:")
         self.pdf.set_font("Arial", size=6)
         self.pdf.multi_cell(w=0, h=5, txt="{}\n\n{}\n{}\n{}\n{}\n".format(self.itemData["SalesOrder"], self.itemData["BillToName"],
                                                                      '\n'.join(self.billToAddress), self.itemData["ShipToName"],
                                                                      '\n'.join(self.shipToAddress)))
         self.pdf.rect(10, 135, 185, 50)

     def addStatement(self):
         self.pdf.set_font("Arial", size=6)
         self.pdf.cell(0, 53, ln=1)
         self.pdf.multi_cell(0, 2, txt="REAL VALUE PRODUCTS CORP complied with each applicable section of FDCA Section 581(27)(A) to (G).")
