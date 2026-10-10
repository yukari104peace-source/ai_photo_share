from pathlib import Path
from datetime import timedelta, timezone

import click
from cachelib import FileSystemCache
from flask import Flask, flash, redirect, render_template, session, url_for, send_from_directory, abort
from flask_login import (
    LoginManager, current_user, login_required, login_user, logout_user,
)
from flask_session import Session
from flask_wtf.csrf import CSRFError, CSRFProtect
from peewee import IntegrityError

from config import load_config
from forms import LoginForm, LogoutForm, RegisterForm, PostForm
from models import Post, User, db, migrate_display_name
from image_utils import InvalidImage, save_post_image


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    if test_config is not None:
        app.config.update(test_config)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("環境変数または.envにSECRET_KEYを設定してください。")

    cache_dir = Path(app.config["SESSION_CACHE_DIR"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    app.config["SESSION_CACHELIB"] = FileSystemCache(str(cache_dir), threshold=0)
    Session(app)
    CSRFProtect(app)
    login_manager = LoginManager(app)
    login_manager.login_view = "login"
    login_manager.login_message = "ログインしてください。"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return None
        return User.get_or_none(User.id == user_id)

    @app.context_processor
    def auth_forms():
        return {"logout_form": LogoutForm(formdata=None)}

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return render_template(
            "errors/error.html",
            message="送信内容を確認できませんでした。画面を開き直して再度お試しください。",
        ), 400

    db.init(str(app.config["DATABASE"]))
    upload_dir = Path(app.config["POST_UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / ".gitkeep").touch(exist_ok=True)

    @app.template_filter("jst")
    def jst(value):
        return value.replace(tzinfo=timezone.utc).astimezone(
            timezone(timedelta(hours=9))
        ).strftime("%Y年%m月%d日 %H:%M")

    @app.errorhandler(413)
    def too_large(error):
        return render_template("errors/error.html", message="送信サイズが大きすぎます。写真は5MB以下にしてください。"), 413

    @app.cli.command("migrate-db")
    def migrate_db():
        with db.connection_context():
            migrate_display_name()
        click.echo("表示名のDB移行が完了しました（既存データは保持）。")

    @app.before_request
    def connect_db():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def close_db(error=None):
        if not db.is_closed():
            db.close()

    @app.cli.command("init-db")
    def init_db():
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
        with db.connection_context():
            with db.atomic():
                db.create_tables([User, Post], safe=True)
                migrate_display_name()
        click.echo("データベースを初期化しました（既存データは保持）。")

    @app.get("/")
    def post_index():
        posts = list(Post.select(Post, User).join(User).order_by(Post.created_at.desc(), Post.id.desc()))
        return render_template("posts/index.html", posts=posts)

    @app.route("/posts/new", methods=["GET", "POST"])
    @login_required
    def post_create():
        form = PostForm()
        if form.validate_on_submit():
            filename = None
            try:
                filename = save_post_image(
                    form.photo.data, app.config["POST_UPLOAD_DIR"],
                    app.config["MAX_IMAGE_BYTES"], app.config["ALLOWED_IMAGE_EXTENSIONS"],
                )
                with db.atomic():
                    Post.create(user=current_user.id, image_filename=filename, caption=form.caption.data or "")
            except InvalidImage as error:
                form.photo.errors.append(str(error))
            except Exception:
                if filename:
                    try:
                        (Path(app.config["POST_UPLOAD_DIR"]) / filename).unlink(missing_ok=True)
                    except OSError:
                        app.logger.exception("保存失敗後の画像削除に失敗しました。")
                app.logger.exception("投稿の保存に失敗しました。")
                return render_template("errors/error.html", message="投稿を保存できませんでした。時間をおいて再度お試しください。"), 500
            else:
                flash("写真を投稿しました。")
                return redirect(url_for("post_index"))
        return render_template("posts/new.html", form=form)

    @app.get("/uploads/posts/<filename>")
    def uploaded_file(filename):
        if not Post.get_or_none(Post.image_filename == filename):
            abort(404)
        response = send_from_directory(app.config["POST_UPLOAD_DIR"], filename)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("post_index"))
        form = RegisterForm()
        if form.validate_on_submit():
            user = User(email=form.email.data, display_name=form.display_name.data)
            user.set_password(form.password.data)
            try:
                with db.atomic():
                    user.save(force_insert=True)
            except IntegrityError:
                if not User.get_or_none(User.email == form.email.data):
                    raise
                form.email.errors.append("このメールアドレスは登録済みです。")
            else:
                flash("登録が完了しました。ログインしてください。")
                return redirect(url_for("login"))
        return render_template("auth/register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("post_index"))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.get_or_none(User.email == form.email.data)
            if user is not None and user.check_password(form.password.data):
                session.clear()
                login_user(user, remember=False)
                # 空セッションではID更新が省略されるため、認証情報を入れた後に更新する。
                app.session_interface.regenerate(session)
                return redirect(url_for("post_index"))
            form.password.errors.append("メールアドレスまたはパスワードが正しくありません。")
        return render_template("auth/login.html", form=form)

    @app.post("/logout")
    @login_required
    def logout():
        logout_user()
        session.clear()
        return redirect(url_for("post_index"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=8000)
