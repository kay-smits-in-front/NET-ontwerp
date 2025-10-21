import logging
import sys


def setup_logging(app):
	log_level = logging.DEBUG if app.config['DEBUG'] else logging.INFO

	logging.basicConfig(
		level=log_level,
		format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
		handlers=[logging.StreamHandler(sys.stdout)]
	)

	app.logger.setLevel(log_level)

	logging.getLogger('werkzeug').setLevel(logging.INFO)
