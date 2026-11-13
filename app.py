import gc
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
import streamlit as st
from PIL import Image
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Unir PDFs Jurisdiccional",
    page_icon="📄",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
LOGO_SIC = IMAGES_DIR / "logo_sic.png"
LOGO_COL = IMAGES_DIR / "logo_colombia.png"

# Límites preventivos. Ajustarlos NO aumenta la RAM ni el almacenamiento
# disponibles en Streamlit Community Cloud.
MAX_TOTAL_UPLOAD_GB = 1.0
MAX_DOWNLOAD_MB = 500
SUPPORTED_TYPES = ["pdf", "png", "jpg", "jpeg", "jfif", "docx"]
IMAGE_TYPES = {"png", "jpg", "jpeg", "jfif"}

# ============================================================
# CONVERSIONES
# ============================================================
def imagen_a_pdf(origen: Path, destino: Path) -> None:
    """Convierte una imagen a PDF. La imagen se conserva sin OCR."""
    with Image.open(origen) as image:
        # PDF necesita RGB o escala de grises. La conversión no aplica OCR.
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(destino, format="PDF", resolution=150.0)


def docx_a_pdf(origen: Path, destino: Path) -> None:
    """
    Conversión básica de texto DOCX a PDF.
    Nota: no reproduce fielmente tablas, imágenes, encabezados ni formato complejo.
    Para fidelidad de Word se recomienda LibreOffice en un servidor de procesamiento.
    """
    doc = Document(str(origen))
    pdf = canvas.Canvas(str(destino), pagesize=letter)
    page_width, page_height = letter
    left_margin = 50
    y = page_height - 55
    line_height = 15

    for paragraph in doc.paragraphs:
        text = paragraph.text or ""
        # Evita que una línea larga salga del área imprimible.
        max_chars = 95
        lines = [text[i:i + max_chars] for i in range(0, len(text), max_chars)] or [""]

        for line in lines:
            if y < 50:
                pdf.showPage()
                y = page_height - 55
            pdf.drawString(left_margin, y, line)
            y -= line_height

    pdf.save()


def escribir_upload_en_disco(uploaded_file, destino: Path) -> None:
    """Escribe el contenido del UploadedFile en un temporal por bloques."""
    uploaded_file.seek(0)
    with destino.open("wb") as output:
        while True:
            chunk = uploaded_file.read(4 * 1024 * 1024)  # 4 MB
            if not chunk:
                break
            output.write(chunk)
    uploaded_file.seek(0)


def agregar_pdf_al_documento(pdf_path: Path, resultado: fitz.Document, nombre: str):
    """Añade páginas al PDF final sin rasterizar ni recomprimir las páginas PDF."""
    source = None
    try:
        source = fitz.open(str(pdf_path))

        if source.is_encrypted:
            # Solo intenta abrir PDF protegidos con contraseña vacía.
            if not source.authenticate(""):
                raise ValueError(
                    f"El PDF '{nombre}' está protegido con contraseña."