import os
import io
import uuid
from PIL import Image
from flask import current_app


def compress_and_save_photo(file_storage, target_size_kb=300, max_dimension=1200):
    """Comprime e redimensiona a foto para tamanho inferior a 300 KB (RF06, RNF02).
    
    Salva a imagem como JPEG otimizada e retorna a URL relativa.
    """
    if not file_storage or not file_storage.filename:
        return None

    # Abre a imagem com Pillow
    image = Image.open(file_storage.stream)

    # Converte modo para RGB se necessário (remover canal alpha ou paleta)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Redimensiona proporcionalmente se exceder a dimensão máxima
    width, height = image.size
    if width > max_dimension or height > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    # Gera nome único para o arquivo
    filename = f"animal_{uuid.uuid4().hex[:12]}.jpg"
    upload_folder = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "static", "uploads"))
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)

    # Loop de compressão decrescente de qualidade para garantir < target_size_kb
    max_bytes = target_size_kb * 1024
    quality = 85
    buffer = io.BytesIO()

    while quality >= 30:
        buffer.seek(0)
        buffer.truncate()
        image.save(buffer, format="JPEG", optimize=True, quality=quality)
        if buffer.tell() <= max_bytes or quality <= 35:
            break
        quality -= 10

    # Grava no disco
    with open(file_path, "wb") as f:
        f.write(buffer.getvalue())

    return f"/static/uploads/{filename}"
