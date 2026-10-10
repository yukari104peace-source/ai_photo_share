from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import Email, EqualTo, InputRequired, Length


def strip_email(value):
    return value.strip() if value else value


class LoginForm(FlaskForm):
    email = StringField("メールアドレス", filters=[strip_email], validators=[
        InputRequired(message="メールアドレスを入力してください。"),
        Email(message="メールアドレスの形式を確認してください。"),
        Length(max=254, message="メールアドレスは254文字以内で入力してください。"),
    ])
    password = PasswordField("パスワード", validators=[
        InputRequired(message="パスワードを入力してください。"),
    ])
    submit = SubmitField("ログイン")


class RegisterForm(LoginForm):
    display_name = StringField("表示名", filters=[strip_email], validators=[
        InputRequired(message="表示名を入力してください。"),
        Length(min=1, max=30, message="表示名は1〜30文字で入力してください。"),
    ])
    password = PasswordField("パスワード", validators=[
        InputRequired(message="パスワードを入力してください。"),
        Length(min=8, message="パスワードは8文字以上で入力してください。"),
    ])
    password_confirm = PasswordField("パスワード（確認）", validators=[
        InputRequired(message="確認用パスワードを入力してください。"),
        EqualTo("password", message="パスワードが一致しません。"),
    ])
    submit = SubmitField("登録")


class LogoutForm(FlaskForm):
    submit = SubmitField("ログアウト")


class PostForm(FlaskForm):
    photo = FileField("写真", validators=[FileRequired(message="写真を選択してください。")])
    caption = TextAreaField("キャプション（任意）", validators=[
        Length(max=200, message="キャプションは200文字以内で入力してください。"),
    ])
    submit = SubmitField("投稿する")
