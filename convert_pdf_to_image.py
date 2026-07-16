import fitz  # PyMuPDF
import os
import datetime

def convert():
    # Paths
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    pdf_path = f'/Users/rodrigoramos/.gemini/antigravity/scratch/analise-mercado-soja/dados/relatorios/diario_soja_{today_str}.pdf'
    
    # Fallback to standard path if dated path doesn't exist
    if not os.path.exists(pdf_path):
        pdf_path = '/Users/rodrigoramos/.gemini/antigravity/scratch/analise-mercado-soja/dados/relatorios/diario_soja.pdf'
        
    png_path = f'/Users/rodrigoramos/Downloads/AGROFOODS_DAILY_MARKET_INTELLIGENCE_{today_str}.png'
    standard_png_path = '/Users/rodrigoramos/Downloads/AGROFOODS_DAILY_MARKET_INTELLIGENCE.png'
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return False
        
    # Open PDF
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)  # Load first page
    
    # Set zoom factor for 300 DPI high-quality rendering
    zoom = 3.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    # Save image files
    pix.save(png_path)
    pix.save(standard_png_path)
    
    print(f"Success: Image saved to {png_path} and {standard_png_path}")
    return True

if __name__ == '__main__':
    convert()
