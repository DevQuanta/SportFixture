from flask import Blueprint

api = Blueprint("api", __name__)

from . import match_routes as match_routes
from . import player_routes as player_routes
from . import routes as routes
