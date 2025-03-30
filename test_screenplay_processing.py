import logging
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch
from nlp_processor import process_screenplay

# Configure logging
logging.basicConfig(level=logging.INFO)

def create_sample_pdf():
    """Create a sample screenplay PDF for testing."""
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
    os.makedirs('uploads', exist_ok=True)
    pdf_path = "uploads/screenplay.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    doc.build(story)
    
    logging.info(f"Screenplay PDF created successfully at {pdf_path}")
    return pdf_path

def test_processing():
    """Test the screenplay processing functionality."""
    # Create the sample PDF
    pdf_path = create_sample_pdf()
    
    # Process the screenplay
    logging.info("Processing screenplay...")
    extracted_data = process_screenplay(pdf_path)
    
    # Log information about extracted data
    logging.info(f"Extracted {len(extracted_data['scenes'])} scenes")
    logging.info(f"Extracted {len(extracted_data['actors'])} actors")
    logging.info(f"Extracted {len(extracted_data['locations'])} locations")
    
    # Print detailed info about actors and their costs
    logging.info("\nACTORS AND COSTS:")
    for actor in extracted_data['actors']:
        logging.info(f"Actor: {actor['name']}, Cost: ${actor.get('cost_per_day', 'N/A'):.2f}, " +
                     f"Importance: {actor.get('importance', 'N/A'):.2f}, " +
                     f"Appearances: {actor.get('appearances', 'N/A')}")
    
    # Print detailed info about locations and their costs
    logging.info("\nLOCATIONS AND COSTS:")
    for location in extracted_data['locations']:
        logging.info(f"Location: {location['name']}, Type: {location.get('type', 'N/A')}, " +
                     f"Cost: ${location.get('cost_per_day', 'N/A'):.2f}")
    
    # Print actor-scene relationships
    logging.info("\nACTOR-SCENE RELATIONSHIPS:")
    for actor_name, scene_numbers in extracted_data['actor_scenes'].items():
        logging.info(f"Actor: {actor_name}, Scenes: {', '.join(scene_numbers)}")
    
    return extracted_data

if __name__ == "__main__":
    test_processing()