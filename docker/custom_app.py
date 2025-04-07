from superset.app import create_app
from flask_appbuilder.security.manager import AUTH_OAUTH
from flask_appbuilder.security.sqla.manager import SecurityManager


# Tu clase personalizada (puede estar en este mismo archivo o importarla)
class CustomJWTAuthSecurityManager(SecurityManager):
    def __init__(self, appbuilder):
        super().__init__(appbuilder)
        self.auth_type = AUTH_OAUTH
        self.oauth_providers = [
            {
                'name': 'jwt',
                'icon': 'fa-user',
                'token_key': 'access_token',
                'remote_app': {
                    'client_id': 'unused',
                    'client_secret': 'unused',
                    'api_base_url': 'http://auth-server/',
                    'access_token_url': 'http://auth-server/token',
                    'authorize_url': 'http://auth-server/authorize',
                    'request_token_url': None,
                    'client_kwargs': {'scope': 'openid'}
                }
            }
        ]


# Crear app y aplicar contexto
app = create_app()

with app.app_context():
    appbuilder = app.appbuilder
    appbuilder.sm = CustomJWTAuthSecurityManager(appbuilder)
