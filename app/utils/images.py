import io
import os
import uuid
from PIL import Image, ImageOps, UnidentifiedImageError
from flask import current_app
from app.utils.validation import ApiError


def compress_and_save_photo(file_storage, target_size_kb=300, max_dimension=1200):
    """Valida, redimensiona e comprime a foto para no máximo 300 KB (RF06, RNF02).

    Reduz a qualidade e, se ainda for preciso, as dimensões, até caber no limite.
    Salva como JPEG e retorna a URL relativa. Arquivo que não é imagem gera ApiError 400.
    """
    if not file_storage or not file_storage.filename:
        return None

    try:
        image = Image.open(file_storage.stream)
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
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

    filename = f"animal_{uuid.uuid4().hex[:12]}.jpg"
    upload_folder = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "static", "uploads"))
    os.makedirs(upload_folder, exist_ok=True)
    with open(os.path.join(upload_folder, filename), "wb") as f:
        f.write(buffer.getvalue())

    return f"/static/uploads/{filename}"
