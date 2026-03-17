import streamlit as st
from pypdf import PdfReader, PdfWriter
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
# ENCABEZADO CON IMÁGENES (IGUAL QUE AUDIENCIAS)
# ---------------------------
c1, c2, c3 = st.columns([1, 4, 1])
with c1:
   if LOGO_COL.exists():
       st.image(str(LOGO_COL), use_container_width=True)
with c2:
   st.markdown("## 📄 Unir PDFs Delegatura para Asuntos Jurisdiccionales")
   st.caption("Herramienta para unir múltiples documentos PDF en uno solo.")
with c3:
   if LOGO_SIC.exists():
       st.image(str(LOGO_SIC), use_container_width=True)
# ---------------------------
# CARGA DE ARCHIVOS
# ---------------------------
st.subheader("Cargar archivos PDF")
uploaded_files = st.file_uploader(
   "Selecciona los PDFs",
   type=["pdf"],
   accept_multiple_files=True
)
# ---------------------------
# PROCESAMIENTO
# ---------------------------
if uploaded_files:
   total = len(uploaded_files)
   st.success(f"✅ {total} archivos cargados")
   # Mostrar lista completa
   with st.expander("📂 Ver lista completa"):
       for i, file in enumerate(uploaded_files, 1):
           st.write(f"{i}. {file.name}")
   # Botón unir
   if st.button("🔗 Unir PDFs"):
       merger = PdfWriter()
       progress = st.progress(0)
       try:
           for i, uploaded_file in enumerate(uploaded_files):
               with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                   tmp_file.write(uploaded_file.read())
                   tmp_file.flush()
                   reader = PdfReader(tmp_file.name)
                   for page in reader.pages:
                       merger.add_page(page)
               progress.progress((i + 1) / total)
           # Guardar resultado
           output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
           merger.write(output_path)
           merger.close()
           with open(output_path, "rb") as f:
               pdf_bytes = f.read()
           st.success("✅ PDFs unidos correctamente")
           st.download_button(
               label="📥 Descargar PDF unido",
               data=pdf_bytes,
               file_name="pdf_unido_jurisdiccional.pdf",
               mime="application/pdf"
           )
       except Exception as e:
           st.error(f"❌ Error: {e}")
 

#### cd "C:\Users\jbohorquez\OneDrive - Directorio SIC\Escritorio\ASUNTOS_JURISDICCIONALES\AUTOMATIZACIONES\ilove_jurs_pdf"      
# streamlit run app.py     