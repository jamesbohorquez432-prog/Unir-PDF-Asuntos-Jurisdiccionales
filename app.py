
import gc
import tempfile
from pathlib import Path

import fitz
import streamlit as st
from PIL import Image
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# ============================================================
# CONFIGURACION GENERAL
# ============================================================

st.set_page_config(
    page_title="Unir PDFs Jurisdiccional",
    page_icon="📄",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "images"

LOGO_SIC = IMAGES_DIR / "logo_sic.png"
LOGO_COL = IMAGES_DIR / "logo_colombia.png"

SUPPORTED_TYPES = [
    "pdf", "png", "jpg", "jpeg", "jfif", "docx"
]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".jfif"}

MAX_FILES = 100
MAX_TOTAL_UPLOAD_MB = 700
MAX_DOWNLOAD_MB = 150

CHUNK_SIZE = 4 * 1024 * 1024


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def format_mb(size_bytes):
    return size_bytes / (1024 * 1024)


def save_uploaded_file(uploaded_file, destination):

    uploaded_file.seek(0)

    with open(destination, "wb") as output:

        while True:
            chunk = uploaded_file.read(CHUNK_SIZE)

            if not chunk:
                break

            output.write(chunk)

    uploaded_file.seek(0)


def convert_image_to_pdf(source_path, destination_path):

    with Image.open(source_path) as image:

        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        image.save(
            destination_path,
            format="PDF",
            resolution=150.0,
        )


def convert_docx_to_pdf(source_path, destination_path):

    document = Document(str(source_path))

    pdf = canvas.Canvas(
        str(destination_path),
        pagesize=letter
    )

    page_width, page_height = letter

    left_margin = 50
    right_margin = 50
    top_margin = 55
    bottom_margin = 50

    usable_width = page_width - left_margin - right_margin

    font_name = "Helvetica"
    font_size = 9
    line_height = 13

    pdf.setFont(font_name, font_size)

    y = page_height - top_margin

    for paragraph in document.paragraphs:

        text = paragraph.text or ""

        max_chars = max(
            30,
            int(usable_width / (font_size * 0.52))
        )

        lines = [
            text[index:index + max_chars]
            for index in range(0, len(text), max_chars)
        ] or [""]

        for line in lines:

            if y < bottom_margin:

                pdf.showPage()
                pdf.setFont(font_name, font_size)

                y = page_height - top_margin

            pdf.drawString(left_margin, y, line)

            y -= line_height

        y -= 4

    pdf.save()


def append_pdf(pdf_path, final_document, display_name):

    source_document = None

    try:

        source_document = fitz.open(str(pdf_path))

        if source_document.is_encrypted:

            authenticated = source_document.authenticate("")

            if not authenticated:

                raise ValueError(
                    f"El PDF '{display_name}' está protegido "
                    "con contraseña."
                )

        if source_document.page_count == 0:

            raise ValueError(
                f"El PDF '{display_name}' no contiene páginas."
            )

        page_count = source_document.page_count

        final_document.insert_pdf(
            source_document,
            links=True,
            annots=True,
        )

        return page_count

    except Exception as error:

        raise RuntimeError(
            f"No se pudo procesar '{display_name}': {error}"
        ) from error

    finally:

        if source_document is not None:
            source_document.close()


def get_extension(filename):

    return Path(filename).suffix.lower()


# ============================================================
# ENCABEZADO
# ============================================================

col_left, col_center, col_right = st.columns([1, 4, 1])

with col_left:

    if LOGO_COL.exists():
        st.image(str(LOGO_COL), use_container_width=True)

with col_center:

    st.markdown(
        "## 📄 Unir documentos – Delegatura para Asuntos Jurisdiccionales"
    )

    st.markdown(
        """
        <p style="color:#C2185B;font-size:14px;">
        Herramienta para consolidar documentos PDF,
        imágenes y archivos Word.
        </p>
        """,
        unsafe_allow_html=True,
    )

with col_right:

    if LOGO_SIC.exists():
        st.image(str(LOGO_SIC), use_container_width=True)


st.divider()

st.info(
    "Los documentos PDF se unen conservando sus páginas originales, "
    "sin rasterizarlas ni aplicar una recompresión intencional."
)

st.warning(
    "Esta versión tiene límites de carga y descarga. "
    "No está diseñada para procesar expedientes de varios GB "
    "en Streamlit Community Cloud."
)


# ============================================================
# CARGA DE DOCUMENTOS
# ============================================================

st.subheader("1. Cargar documentos")

uploaded_files = st.file_uploader(
    "Selecciona los documentos en el orden en que deseas unirlos.",
    type=SUPPORTED_TYPES,
    accept_multiple_files=True,
    help="Se respeta el orden mostrado en la lista.",
)


if uploaded_files:

    total_files = len(uploaded_files)

    total_bytes = sum(
        file.size for file in uploaded_files
    )

    total_mb = format_mb(total_bytes)

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric(
        "Documentos seleccionados",
        f"{total_files:,}"
    )

    metric2.metric(
        "Tamaño total",
        f"{total_mb:,.1f} MB"
    )

    metric3.metric(
        "Tamaño en GB",
        f"{total_mb / 1024:,.2f} GB"
    )

    with st.expander("📂 Revisar documentos"):

        for number, uploaded_file in enumerate(
            uploaded_files,
            start=1
        ):

            st.write(
                f"{number}. {uploaded_file.name} "
                f"({format_mb(uploaded_file.size):,.1f} MB)"
            )

    too_many_files = total_files > MAX_FILES

    too_large = total_mb > MAX_TOTAL_UPLOAD_MB

    if too_many_files:

        st.error(
            f"El máximo permitido en esta versión es "
            f"{MAX_FILES} documentos."
        )

    if too_large:

        st.error(
            f"El tamaño total supera el límite preventivo "
            f"de {MAX_TOTAL_UPLOAD_MB} MB."
        )

    if not too_many_files and not too_large:

        st.caption(
            "Verifica el orden de los documentos antes de continuar."
        )

        if st.button(
            "🔗 Unir documentos",
            type="primary"
        ):

            progress = st.progress(0)

            status = st.empty()

            result_message = st.empty()

            success_files = []
            failed_files = []

            total_pages = 0

            try:

                with tempfile.TemporaryDirectory(
                    prefix="unificador_jurisdiccional_"
                ) as temp:

                    temp_dir = Path(temp)

                    output_path = (
                        temp_dir /
                        "pdf_unido_jurisdiccional.pdf"
                    )

                    final_document = fitz.open()

                    try:

                        for index, uploaded_file in enumerate(
                            uploaded_files,
                            start=1
                        ):

                            extension = get_extension(
                                uploaded_file.name
                            )

                            input_path = (
                                temp_dir /
                                f"entrada_{index:04d}{extension}"
                            )

                            converted_path = (
                                temp_dir /
                                f"convertido_{index:04d}.pdf"
                            )

                            status.info(
                                f"Procesando documento {index} "
                                f"de {total_files}: "
                                f"{uploaded_file.name}"
                            )

                            try:

                                save_uploaded_file(
                                    uploaded_file,
                                    input_path
                                )

                                if extension == ".pdf":

                                    pdf_to_append = input_path

                                elif extension in IMAGE_EXTENSIONS:

                                    convert_image_to_pdf(
                                        input_path,
                                        converted_path
                                    )

                                    pdf_to_append = converted_path

                                elif extension == ".docx":

                                    convert_docx_to_pdf(
                                        input_path,
                                        converted_path
                                    )

                                    pdf_to_append = converted_path

                                else:

                                    raise ValueError(
                                        f"Formato no admitido: {extension}"
                                    )

                                pages = append_pdf(
                                    pdf_to_append,
                                    final_document,
                                    uploaded_file.name
                                )

                                total_pages += pages

                                success_files.append(
                                    uploaded_file.name
                                )

                            except Exception as error:

                                failed_files.append(
                                    f"{uploaded_file.name}: {error}"
                                )

                            finally:

                                for temporary_path in (
                                    input_path,
                                    converted_path
                                ):

                                    try:

                                        temporary_path.unlink(
                                            missing_ok=True
                                        )

                                    except OSError:
                                        pass

                                gc.collect()

                            progress.progress(
                                index / total_files
                            )

                        if final_document.page_count == 0:

                            raise RuntimeError(
                                "No se pudo incorporar ninguna página."
                            )

                        status.info(
                            "Guardando el documento consolidado..."
                        )

                        final_document.save(
                            str(output_path),
                            garbage=0,
                            deflate=False,
                            clean=False,
                        )

                    finally:

                        final_document.close()

                    output_size = output_path.stat().st_size

                    output_mb = format_mb(output_size)

                    st.success(
                        f"Proceso terminado. "
                        f"Se unieron {len(success_files)} documentos "
                        f"y {total_pages:,} páginas."
                    )

                    result_col1, result_col2 = st.columns(2)

                    result_col1.metric(
                        "Documentos incorporados",
                        len(success_files)
                    )

                    result_col2.metric(
                        "Tamaño del PDF final",
                        f"{output_mb:,.1f} MB"
                    )

                    if failed_files:

                        st.warning(
                            f"{len(failed_files)} documentos "
                            "no pudieron incorporarse."
                        )

                        with st.expander("Ver errores"):

                            for error in failed_files:
                                st.write(f"• {error}")

                    if output_mb <= MAX_DOWNLOAD_MB:

                        with open(output_path, "rb") as output_file:

                            pdf_data = output_file.read()

                        st.download_button(
                            label="📥 Descargar PDF unido",
                            data=pdf_data,
                            file_name="pdf_unido_jurisdiccional.pdf",
                            mime="application/pdf",
                            type="primary",
                        )

                    else:

                        st.error(
                            f"El PDF final pesa {output_mb:,.1f} MB. "
                            f"Supera el límite de descarga de "
                            f"{MAX_DOWNLOAD_MB} MB."
                        )

                    if failed_files:

                        st.info(
                            "El PDF final contiene únicamente "
                            "los documentos procesados correctamente. "
                            "Revisa los errores antes de utilizarlo."
                        )

                    status.success(
                        "Proceso finalizado."
                    )

            except Exception as error:

                result_message.error(
                    f"No fue posible completar la unión: {error}"
                )

            finally:

                gc.collect()

else:

    st.caption(
        "Selecciona documentos para comenzar."
    )


# ============================================================
# PIE DE PAGINA
# ============================================================

st.divider()

st.caption(
    "Unificador PDF – Delegatura para Asuntos Jurisdiccionales. "
    "Verifica el resultado y el orden de las páginas antes de utilizarlo."
)
