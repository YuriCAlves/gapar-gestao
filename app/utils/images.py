import io
import uuid
from PIL import Image, ImageOps, UnidentifiedImageError
from app.utils.storage import save_photo
from app.utils.validation import ApiError


def compress_photo(file_storage, target_size_kb=300, max_dimension=1200):
    """Valida, redimensiona e comprime a foto para no máximo 300 KB (RF06, RNF02).

    Reduz a qualidade e, se ainda for preciso, as dimensões, até caber no limite.
    Devolve os bytes do JPEG. Arquivo que não é imagem gera ApiError 400.
    """
    try:
        image = Image.open(file_storage.stream)
        image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ApiError("Imagem inválida", 400, "O arquivo enviado não é uma imagem válida (use JPG, PNG ou WebP).")

    image = ImageOps.exif_transpose(image)  # respeita a rotação da câmera do celular
    if image.mode != "RGB":
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        image = background

    if max(image.size) > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    max_bytes = target_size_kb * 1024
    buffer = io.BytesIO()
    quality = 85
    while True:
        buffer.seek(0)
        buffer.truncate()
        image.save(buffer, format="JPEG", optimize=True, quality=quality)
        if buffer.tell() <= max_bytes:
            break
        if quality > 40:
            quality -= 10
        elif min(image.size) > 200:
            image = image.resize((int(image.width * 0.8), int(image.height * 0.8)), Image.Resampling.LANCZOS)
        else:
            raise ApiError("Imagem inválida", 400, "Não foi possível reduzir a imagem para 300 KB.")

    return buffer.getvalue()


def compress_and_save_photo(file_storage, target_size_kb=300, max_dimension=1200):
    """Comprime a foto (no máximo 300 KB) e grava no armazenamento configurado.

    Devolve a URL da foto: pública do Supabase Storage quando ele está configurado, ou
    `/static/uploads/...` no disco local. Sem arquivo, devolve None.
    """
    if not file_storage or not file_storage.filename:
        return None

    conteudo = compress_photo(file_storage, target_size_kb=target_size_kb, max_dimension=max_dimension)
    filename = f"animal_{uuid.uuid4().hex[:12]}.jpg"
    return save_photo(conteudo, filename)
