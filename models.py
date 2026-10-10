from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from peewee import (
    AutoField,
    CharField,
    Check,
    DateTimeField,
    ForeignKeyField,
    Model,
    SqliteDatabase,
    TextField,
)


db = SqliteDatabase(None, pragmas={"foreign_keys": 1})


def utc_now():
    # DB内はタイムゾーン情報なしのUTCに統一する。
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BaseModel(Model):
    class Meta:
        database = db


class User(UserMixin, BaseModel):
    id = AutoField()
    display_name = CharField(max_length=30, constraints=[Check("length(trim(display_name)) BETWEEN 1 AND 30")])
    email = CharField(max_length=254, unique=True, collation="BINARY")
    password_hash = TextField()
    created_at = DateTimeField(default=utc_now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    class Meta:
        table_name = "users"


class Post(BaseModel):
    id = AutoField()
    user = ForeignKeyField(User, backref="posts", on_delete="RESTRICT")
    image_filename = CharField(max_length=255, unique=True)
    caption = CharField(
        max_length=200,
        default="",
        constraints=[Check("length(caption) <= 200")],
    )
    created_at = DateTimeField(default=utc_now)

    class Meta:
        table_name = "posts"


def migrate_display_name():
    """既存のID・認証情報・投稿を保ち、表示名だけを追加する。"""
    with db.atomic():
        if User.table_exists() and "display_name" not in {
            column.name for column in db.get_columns("users")
        }:
            db.execute_sql(
                "ALTER TABLE users ADD COLUMN display_name VARCHAR(30) "
                "NOT NULL DEFAULT 'ユーザー' "
                "CHECK(length(trim(display_name)) BETWEEN 1 AND 30)"
            )
            db.execute_sql("UPDATE users SET display_name = 'ユーザー' || id")
