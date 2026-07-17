import streamlit as st
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from PIL import Image
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile
from pathlib import Path

# ---------------------------
# Configuración
# ---------------------------
st.set_page_config(page_title="Unir PDFs Jurisdiccional", layout="wide")

# ---------------------------
# Rutas
# ---------------------------
BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"

LOGO_SIC = IMAGES_DIR / "logo_sic.png"
LOGO_COL = IMAGES_DIR / "logo_colombia.png"

# ---------------------------
# FUNCIONES DE CONVERSIÓN
# ---------------------------
def imagen_a_pdf(path_img):
    image = Image.open(path_img)

    if image.mode != "RGB":
        image = image.convert("RGB")

    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    image.save(temp_pdf.name)

    return temp_pdf.name


def docx_a_pdf(path_docx):
    doc = Document(path_docx)

    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp_pdf.name, pagesize=letter)

    y = 750

    for p in doc.paragraphs:
        c.drawString(50, y, p.text)
        y -= 15

        if y < 50:
            c.showPage()
            y = 750

    c.save()

    return temp_pdf.name


# ---------------------------
# ENCABEZADO
# ---------------------------
c1, c2, c3 = st.columns([1, 4, 1])

with c1:
    if LOGO_COL.exists():
        st.image(str(LOGO_COL), use_container_width=True)

with c2:
    st.markdown("## 📄 Unir PDFs Delegatura para Asuntos Jurisdiccionales")
    st.markdown(
        """
        <style>
        .texto-fucsia{
            color:#C2185B !important;
            font-size:14px;
        }
        </style>

        <p class="texto-fucsia">
        Herramienta para unir múltiples documentos (PDF, imágenes y Word) en un solo archivo.
        </p>
        """,
        unsafe_allow_html=True
    )

with c3:
    if LOGO_SIC.exists():
        st.image(str(LOGO_SIC), use_container_width=True)

# ---------------------------
# CARGA DE ARCHIVOS
# ---------------------------
st.subheader("Cargar archivos")

uploaded_files = st.file_uploader(
    "Selecciona archivos (PDF, PNG, JPG, JPEG, JFIF, DOCX)",
    type=["pdf", "png", "jpg", "jpeg", "jfif", "docx"],
    accept_multiple_files=True
)

# ---------------------------
# PROCESAMIENTO
# ---------------------------
if uploaded_files:

    total = len(uploaded_files)

    st.success(f"✅ {total} archivos cargados")

    with st.expander("📂 Ver lista completa"):
        for i, archivo in enumerate(uploaded_files, start=1):
            st.write(f"{i}. {archivo.name}")

    if st.button("🔗 Unir archivos"):

        merger = PdfWriter()
        progress = st.progress(0)

        try:

            for i, uploaded_file in enumerate(uploaded_files):

                suffix = uploaded_file.name.split(".")[-1].lower()

                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix="." + suffix
                )

                temp_file.write(uploaded_file.read())
                temp_file.flush()

                path = temp_file.name

                # ---------------------
                # Convertir imágenes
                # ---------------------
                if suffix in ["png", "jpg", "jpeg", "jfif"]:
                    path = imagen_a_pdf(path)

                # ---------------------
                # Convertir Word
                # ---------------------
                elif suffix == "docx":
                    path = docx_a_pdf(path)

                # ---------------------
                # Leer PDF
                # ---------------------
                try:

                    reader = PdfReader(path)

                    if reader.is_encrypted:

                        try:
                            reader.decrypt("")
                        except Exception:
                            st.error(
                                f"❌ El archivo '{uploaded_file.name}' está protegido con contraseña y no puede unirse."
                            )
                            continue

                    for page in reader.pages:
                        merger.add_page(page)

                except PdfReadError as e:
                    st.error(f"❌ No fue posible leer '{uploaded_file.name}'")
                    st.exception(e)
                    continue

                progress.progress((i + 1) / total)

            # ---------------------
            # Guardar PDF final
            # ---------------------
            output_path = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".pdf"
            ).name

            merger.write(output_path)
            merger.close()

            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

            st.success("✅ Archivos unidos correctamente")

            st.download_button(
                "📥 Descargar PDF unido",
                pdf_bytes,
                file_name="pdf_unido_jurisdiccional.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")
 

#### cd "C:\Users\jbohorquez\OneDrive - Directorio SIC\Escritorio\ASUNTOS_JURISDICCIONALES\AUTOMATIZACIONES\ilove_jurs_pdf"      
# streamlit run app.py     