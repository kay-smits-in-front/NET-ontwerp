import os
import sys

from flask import Flask, render_template

from config import config
from core.logging_config import setup_logging


def create_app(config_name='development'):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.config.from_object(config[config_name])
    setup_logging(app)

    apps = load_apps()

    @app.route('/')
    def index():
        return render_template('index.html', apps=apps)

    for app_info in apps:
        try:
            module = __import__(f'apps.{app_info["module"]}.routes', fromlist=['bp'])
            app.register_blueprint(module.bp)
        except ImportError as e:
            app.logger.error(f'Error importing {app_info["module"]}: {e}')

    return app


def load_apps():
    apps = []
    apps_dir = 'apps'

    ignore_folders = {'__pycache__', '.idea', '.git', '.vscode'}

    if os.path.exists(apps_dir):
        for app_name in os.listdir(apps_dir):
            app_path = os.path.join(apps_dir, app_name)
            if (
                os.path.isdir(app_path)
                and not app_name.startswith('__')
                and app_name not in ignore_folders
            ):
                apps.append(
                    {
                        'name': app_name.replace('_', ' ').title(),
                        'description': f'Beschrijving voor {app_name}',
                        'route': f'{app_name}.main',
                        'module': app_name,
                    }
                )

    return apps
