from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
# In-memory storage — fine for this single-instance deployment. Multiple
# app replicas would each track limits independently unless backed by a
# shared store (e.g. Redis), so this wouldn't hold up as-is if scaled out.
limiter = Limiter(key_func=get_remote_address)
