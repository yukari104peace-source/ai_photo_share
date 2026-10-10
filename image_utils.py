from io import BytesIO
from pathlib import Path
from uuid import uuid4
import warnings

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename


class InvalidImage(ValueError):
    pass


def save_post_image(upload, directory, max_bytes, allowed_extensions):
    # 日本語だけの名前も受け付け、保存には元の名前を使用しない。
    extension = Path(upload.filename or "").suffix.lower().lstrip(".")
    if extension not in allowed_extensions:
        raise InvalidImage("PNG・JPG・JPEG・GIFの画像を選択してください。")
    data = upload.stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise InvalidImage("画像は5MB以下にしてください。")
    formats = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG", "gif": "GIF"}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format != formats[extension]:
                    raise InvalidImage("拡張子と画像の形式が一致しません。")
                image.verify()
            # verifyだけでは検出されない破損も、全フレームの読み込みで確認する。
            with Image.open(BytesIO(data)) as image:
                total_pixels = 0
                frame = 0
                while True:
                    total_pixels += image.width * image.height
                    if total_pixels > 40_000_000 or frame >= 200:
                        raise InvalidImage("画像の画素数またはフレーム数が多すぎます。")
                    image.load()
                    frame += 1
                    try:
                        image.seek(frame)
                    except EOFError:
                        break
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        if isinstance(error, InvalidImage):
            raise
        raise InvalidImage("画像を読み込めません。正常な画像を選択してください。") from error

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(f"{uuid4().hex}.{extension}")
    path = directory / filename
    # 排他的に作成し、同名のファイルを上書きしない。
    with path.open("xb") as output:
        try:
            output.write(data)
        except OSError:
            path.unlink(missing_ok=True)
            raise
    return filename
