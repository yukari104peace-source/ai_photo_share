from pathlib import Path

import click
from flask import Flask, render_template

from models import Post, User, db


def create_app(test_config=None):
    app = Flask(__name__, static_folder=None)
    app.config.from_mapping(
        DATABASE=Path(app.root_path) / "instance" / "app.sqlite3",
    )
    if test_config is not None:
        app.config.update(test_config)

    db.init(str(app.config["DATABASE"]))

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
        click.echo("データベースを初期化しました（既存データは保持）。")

    @app.get("/")
    def post_index():
        return render_template("posts/index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(port=8000)
