import os

class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "ankush-katkurwar")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "Anku$h9844.")
    DATABASE = os.getenv("DATABASE", "facebook_clone")
    JWT_SECRET_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJPbmxpbmUgSldUIEJ1YiI6IkpvaG5ueSIsIlN1cm5hbWUiOiJSb2NrZXQiLCJFbWFpbCI6Impyb2NrZXRAZXhhbXBsZS5jb20iLCJSb2xlIjpbIk1hbmFnZXIiLCJQcm9qZWN0IEFkbWluaXN0cmF0b3IiXX0.RSq0eQtMWrxk4xxSiF8kD9B1L_8WExdEy-pCzrwSuYY"
