import click
import os
import shutil
import subprocess
import sys


@click.group()
def cli():
	"""Flask App Framework Management CLI"""
	pass


@cli.command()
@click.argument('app_name')
def new_app(app_name):
	"""Create a new app with template structure"""
	create_new_app(app_name)


@cli.command()
def test():
	"""Run tests for all apps"""
	run_tests()


@cli.command()
@click.option('--target', default='G:\\Tools\\CompanyApps', help='Deployment target path')
def deploy(target):
	"""Deploy to production"""
	deploy_to_production(target)


def create_new_app(app_name):
	app_dir = f'apps/{app_name}'

	if os.path.exists(app_dir):
		click.echo(f'App {app_name} already exists!')
		return

	# Create directories
	os.makedirs(f'{app_dir}/templates', exist_ok=True)

	# Create __init__.py
	with open(f'{app_dir}/__init__.py', 'w') as f:
		f.write('')

	# Create routes.py template
	routes_template = f'''from flask import Blueprint, render_template

bp = Blueprint('{app_name}', __name__, url_prefix='/{app_name}')

@bp.route('/')
def main():
    return render_template('{app_name}/{app_name}.html', 
                         title='{app_name.replace("_", " ").title()}',
                         data={{'message': 'Welkom bij {app_name}!'}})
'''

	with open(f'{app_dir}/routes.py', 'w') as f:
		f.write(routes_template)

	# Create template
	template_content = f'''{{%% extends "base.html" %%}}

{{%% block title %%}}{{{{ title }}}} - Company Apps{{%% endblock %%}}

{{%% block content %%}}
<div class="max-w-4xl mx-auto">
    <div class="app-card rounded-2xl p-8">
        <h2 class="text-3xl font-bold text-white mb-6">{{{{ title }}}}</h2>

        <div class="bg-blue-600 bg-opacity-20 border border-blue-400 border-opacity-30 rounded-lg p-4 mb-8">
            <p class="text-blue-100">{{{{ data.message }}}}</p>
        </div>

        <div class="space-y-4">
            <button class="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg transition-all">
                Functie 1
            </button>
            <button class="bg-yellow-600 hover:bg-yellow-700 text-white px-6 py-3 rounded-lg transition-all ml-4">
                Functie 2
            </button>
        </div>

        <div class="mt-8">
            <a href="/" class="text-blue-300 hover:text-white transition-colors">← Terug naar hoofdmenu</a>
        </div>
    </div>
</div>
{{%% endblock %%}}
'''

	os.makedirs(f'templates/{app_name}', exist_ok=True)
	with open(f'templates/{app_name}/{app_name}.html', 'w') as f:
		f.write(template_content)

	click.echo(f'✓ App {app_name} created successfully!')
	click.echo(f'✓ Files created:')
	click.echo(f'  - apps/{app_name}/routes.py')
	click.echo(f'  - templates/{app_name}/{app_name}.html')


def run_tests():
	click.echo('Running tests...')
	result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '-v'],
	                        capture_output=True, text=True)
	click.echo(result.stdout)
	if result.stderr:
		click.echo(result.stderr)


def deploy_to_production(target_path):
	click.echo(f'Deploying to {target_path}...')
	# Implementation comes later
	click.echo('Deploy function not implemented yet')


@cli.command()
@click.option('--app', help='Specific app to lint')
@click.option('--fix', is_flag=True, help='Auto-fix issues')
def lint(app, fix):
	"""Run Ruff linting on code"""
	if app:
		target = f'apps/{app}/'
		if not os.path.exists(target):
			click.echo(f'App {app} not found!')
			return
	else:
		target = '.'

	click.echo(f'Running Ruff lint on {target}...')

	cmd = ['ruff', 'check', target]
	if fix:
		cmd.append('--fix')

	try:
		result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')

		if result.stdout:
			click.echo(result.stdout)
		if result.stderr:
			click.echo(result.stderr)

		if result.returncode == 0:
			click.echo('✅ All checks passed!')
		else:
			click.echo('⚠️ Issues found. Use --fix to auto-repair.')

	except Exception as e:
		click.echo(f'Error running Ruff: {e}')


@cli.command()
@click.option('--app', help='Specific app to format')
def format_code(app):
	"""Format code with Ruff"""
	if app:
		target = f'apps/{app}/'
		if not os.path.exists(target):
			click.echo(f'App {app} not found!')
			return
	else:
		target = '.'

	click.echo(f'Formatting code in {target}...')

	result = subprocess.run(['ruff', 'format', target], capture_output=True, text=True)

	if result.stdout:
		click.echo(result.stdout)
	if result.returncode == 0:
		click.echo('Code formatted successfully!')
	else:
		click.echo('Formatting failed!')
		if result.stderr:
			click.echo(result.stderr)


if __name__ == '__main__':
	cli()