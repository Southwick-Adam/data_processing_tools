from reportlab.pdfgen import canvas
from reportlab.platypus import (SimpleDocTemplate, Paragraph, PageBreak, Image, Spacer, Table, TableStyle)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import LETTER, inch
from reportlab.graphics.shapes import Line, Drawing
from reportlab.lib.colors import Color

class FooterCanvas(canvas.Canvas):

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        self.width, self.height = LETTER

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            if (self._pageNumber > 1):
                self.draw_canvas(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_canvas(self, page_count):
        page = "Page %s of %s" % (self._pageNumber, page_count)
        x = 128
        self.saveState()
        self.setStrokeColorRGB(0, 0, 0)
        self.setLineWidth(0.5)
        self.drawImage("logos/test.png", self.width-inch*8-5, self.height-50, width=100, height=20, preserveAspectRatio=True)
        self.drawImage("logos/test.png", self.width - inch * 2, self.height-50, width=100, height=30, preserveAspectRatio=True, mask='auto')
        self.line(30, 740, LETTER[0] - 50, 740)
        self.line(66, 78, LETTER[0] - 66, 78)
        self.setFont('Times-Roman', 10)
        self.drawString(LETTER[0]-x, 65, page)
        self.restoreState()

class PDFReport:

    def __init__(self, path, input_data):
        self.path = path
        self.styleSheet = getSampleStyleSheet()
        self.elements = []

        # colors - Azul turkeza 367AB3
        self.colorOhkaGreen0 = Color((45.0/255), (166.0/255), (153.0/255), 1)
        self.colorOhkaGreen1 = Color((182.0/255), (227.0/255), (166.0/255), 1)
        self.colorOhkaGreen2 = Color((140.0/255), (222.0/255), (192.0/255), 1)
        self.colorOhkaBlue0 = Color((54.0/255), (122.0/255), (179.0/255), 1)
        self.colorOhkaBlue1 = Color((122.0/255), (180.0/255), (225.0/255), 1)
        self.colorOhkaGreenLineas = Color((50.0/255), (140.0/255), (140.0/255), 1)

        self.PagesHeader()
        self.TableMaker(input_data)
        # Build
        self.doc = SimpleDocTemplate(path, pagesize=LETTER)
        self.doc.multiBuild(self.elements, canvasmaker=FooterCanvas)
        print("Report PDF made")

    def PagesHeader(self):
        psHeaderText = ParagraphStyle('Hed0', fontSize=16, alignment=TA_LEFT, borderWidth=3, textColor=self.colorOhkaGreen0)
        text = 'Missing Value Report'
        paragraphReportHeader = Paragraph(text, psHeaderText)
        self.elements.append(paragraphReportHeader)

        spacer = Spacer(10, 10)
        self.elements.append(spacer)

        d = Drawing(500, 1)
        line = Line(-15, 0, 483, 0)
        line.strokeColor = self.colorOhkaGreenLineas
        line.strokeWidth = 2
        d.add(line)
        self.elements.append(d)

        spacer = Spacer(10, 1)
        self.elements.append(spacer)

        d = Drawing(500, 1)
        line = Line(-15, 0, 483, 0)
        line.strokeColor = self.colorOhkaGreenLineas
        line.strokeWidth = 0.5
        d.add(line)
        self.elements.append(d)

        spacer = Spacer(10, 22)
        self.elements.append(spacer)

    def TableMaker(self, input_data):        
        psHeaderText = ParagraphStyle('Hed0', fontSize=12, alignment=TA_LEFT, borderWidth=3, textColor=self.colorOhkaBlue0)
        text = 'Missing Values By Percentage'
        paragraphReportHeader = Paragraph(text, psHeaderText)
        self.elements.append(paragraphReportHeader)

        spacer = Spacer(10, 22)
        self.elements.append(spacer)
        """
        Create the line items
        """
        
        alignStyle = [ParagraphStyle(name="01", alignment=TA_LEFT),
                      ParagraphStyle(name="02", alignment=TA_LEFT),
                      ParagraphStyle(name="03", alignment=TA_LEFT),
                      ParagraphStyle(name="04", alignment=TA_LEFT)]
        
        d = []
        textData = ["Feature", "Document", "Missing", "Importance"]
        columnNumber = 0 
        fontSize = 12
        for text in textData:
            ptext = "<font size='%s'><b>%s</b></font>" % (fontSize, text)
            titlesTable = Paragraph(ptext, alignStyle[columnNumber])
            d.append(titlesTable)
            columnNumber += 1   

        data = [d]
        formattedLineData = []

        for row in input_data:
            feature = row[0]
            doc = row[1]
            value = row[2]
            group = row[3]
            
            if value == 0:
                continue
            
            imp = "Other"
            if group == 0:
                imp = "Primary"
            elif group == 1:
                imp = "Secondary"
            
            lineData = [feature, doc, f"{value}%", imp]

            columnNumber = 0
            for item in lineData:
                ptext = "<font size='%s'>%s</font>" % (fontSize-1, item)
                p = Paragraph(ptext, alignStyle[columnNumber])
                formattedLineData.append(p)
                columnNumber += 1
            data.append(formattedLineData)
            formattedLineData = []
        

        table = Table(data, colWidths=[150, 200, 80, 80], rowHeights=[30] * len(data))
        tStyle = TableStyle([ 
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ("ALIGN", (1, 0), (1, -1), 'RIGHT'),
                ('LINEABOVE', (0, 0), (-1, -1), 1, self.colorOhkaBlue1),
                ('BACKGROUND',(0, 0), (-1, 0), self.colorOhkaGreenLineas)
                ])
        table.setStyle(tStyle)
        self.elements.append(table)

def make_report_pdf(data):
    return PDFReport('report/missing_values_report.pdf', data)