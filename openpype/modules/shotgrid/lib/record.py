
class Credentials:
    login = None
    password = None

    def __init__(self, login, password) -> None:
        super().__init__()
        self.login = login
        self.password = password

    def is_empty(self):
        return not (self.login and self.password)

    @staticmethod
    def login_key_prefix():
        return "login"

    @staticmethod
    def password_key_prefix():
        return "password"
