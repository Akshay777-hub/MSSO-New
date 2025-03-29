from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch

# Create custom styles
styles = getSampleStyleSheet()
styles['Title'].fontSize = 16
styles['Title'].alignment = TA_CENTER
styles['Title'].spaceAfter = 20

# Add screenplay-specific styles
screenplay_styles = {
    'SceneHeading': ParagraphStyle(name='SceneHeading', fontSize=12, spaceAfter=10, fontName='Courier-Bold'),
    'Action': ParagraphStyle(name='Action', fontSize=12, spaceAfter=10, fontName='Courier'),
    'Character': ParagraphStyle(name='Character', fontSize=12, spaceAfter=0, fontName='Courier-Bold'),
    'Dialogue': ParagraphStyle(name='Dialogue', fontSize=12, spaceAfter=10, fontName='Courier', leftIndent=1*inch, rightIndent=1*inch),
    'Parenthetical': ParagraphStyle(name='Parenthetical', fontSize=12, spaceAfter=0, fontName='Courier', leftIndent=0.75*inch, rightIndent=1.75*inch),
    'Transition': ParagraphStyle(name='Transition', fontSize=12, spaceAfter=10, fontName='Courier-Bold', alignment=TA_RIGHT)
}

# Read the screenplay text file
with open('sample_screenplay.txt', 'r') as file:
    content = file.readlines()

# Process the content for PDF formatting
story = []
i = 0
while i < len(content):
    line = content[i].strip()
    
    # Title
    if "TITLE:" in line:
        story.append(Paragraph(line.replace("TITLE:", "").strip(), styles['Title']))
    
    # Scene headings (typically in all caps and start with INT. or EXT.)
    elif line.startswith("INT.") or line.startswith("EXT.") or line.startswith("FADE IN") or line.startswith("FADE OUT"):
        story.append(Paragraph(line, screenplay_styles['SceneHeading']))
    
    # Transitions (typically in all caps and ends with :)
    elif line.endswith("OUT.") or line == "THE END":
        story.append(Paragraph(line, screenplay_styles['Transition']))
    
    # Character names (typically in all caps, usually followed by dialogue)
    elif line.isupper() and i+1 < len(content) and not (line.startswith("INT.") or line.startswith("EXT.")):
        story.append(Paragraph(line, screenplay_styles['Character']))
        i += 1
        # Check for parenthetical
        if i < len(content) and content[i].strip().startswith("("):
            story.append(Paragraph(content[i].strip(), screenplay_styles['Parenthetical']))
            i += 1
        # Add dialogue
        dialogue = []
        while i < len(content) and content[i].strip() and not content[i].strip().isupper():
            dialogue.append(content[i].strip())
            i += 1
        if dialogue:
            story.append(Paragraph("<br/>".join(dialogue), screenplay_styles['Dialogue']))
        continue  # Skip the normal increment since we've manually advanced
    
    # Action (everything else)
    elif line:
        story.append(Paragraph(line, screenplay_styles['Action']))
    
    # Empty lines become spacers
    elif not line and i > 0 and not content[i-1].strip():
        story.append(Spacer(1, 12))
    
    i += 1

# Create PDF
doc = SimpleDocTemplate("uploads/screenplay.pdf", pagesize=letter)
doc.build(story)

print("Screenplay PDF created successfully at uploads/screenplay.pdf")