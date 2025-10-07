from flask import Flask, render_template
import sys
import os


def create_app():
	# Add project root to python path
	project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	if project_root not in sys.path:
		sys.path.insert(0, project_root)

	app = Flask(__name__, template_folder='../templates', static_folder='../static')

	# Load apps
	apps = load_apps()

	@app.route('/')
	def index():
		return render_template('index.html', apps=apps)

	# Register app blueprints
	for app_info in apps:
		try:
			module = __import__(f'apps.{app_info["module"]}.routes', fromlist=['bp'])
			app.register_blueprint(module.bp)
		except ImportError as e:
			print(f"Error importing {app_info['module']}: {e}")

	return app


def load_apps():
	apps = []
	apps_dir = 'apps'

	# Folders to ignore
	ignore_folders = {'__pycache__', '.idea', '.git', '.vscode'}

	if os.path.exists(apps_dir):
		for app_name in os.listdir(apps_dir):
			app_path = os.path.join(apps_dir, app_name)
			if (os.path.isdir(app_path) and
					not app_name.startswith('__') and
					app_name not in ignore_folders):
				apps.append({
					'name': app_name.replace('_', ' ').title(),
					'description': f'Beschrijving voor {app_name}',
					'route': f'{app_name}.main',
					'module': app_name
				})

	return apps