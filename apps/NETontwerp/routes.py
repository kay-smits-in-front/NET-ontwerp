import os
from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename


bp = Blueprint('NETontwerp', __name__, url_prefix='/NETontwerp')

UPLOAD_FOLDER = 'uploads/net_ontwerp'
ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_upload_folder():
	if not os.path.exists(UPLOAD_FOLDER):
		os.makedirs(UPLOAD_FOLDER)


@bp.route('/')
def main():
	return render_template('NETontwerp/NETontwerp.html',
	                       title='NETontwerp',
	                       data={'message': 'Welkom bij NETontwerp!'})


@bp.route('/berekening', methods=['GET', 'POST'])
def berekening():
	if request.method == 'POST':
		return handle_form_submission()

	cable_types = [
		'4*240mm2 Al',
		'4*150mm2 Al (basis)',
		'4*95mm2 Al',
		'4*50mm2 Al',
		'4*16mm2 Cu',
		'4*6mm2 Cu'
	]

	station_types = [
		'pacto 10 tot 400 kva',
		'pacto 20 tot 630kva (most preferred)',
		'pacto 25 tot 630 kva maximaal 1000Amperé',
		'akagkps3 tot 630kva',
		'Batenburg tot 630kva',
		'diabolo tot 630kva'
	]

	return render_template('NETontwerp/berekeningen.html',
	                       cable_types=cable_types,
	                       station_types=station_types)


def handle_form_submission():
	ensure_upload_folder()

	# Handle file upload
	uploaded_file = None
	if 'pdf_file' in request.files:
		file = request.files['pdf_file']
		if file and file.filename != '' and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			filepath = os.path.join(UPLOAD_FOLDER, filename)
			file.save(filepath)
			uploaded_file = filename
		elif file and file.filename != '':
			flash('Alleen PDF bestanden zijn toegestaan', 'error')
			return redirect(url_for('NETontwerp.berekeningen'))

	# Collect form data
	form_data = {
		'buurtcode': request.form.get('buurtcode'),
		'ontwerp_kaders_check': 'ontwerp_kaders_check' in request.form,
		'aantal_woningen': request.form.get('aantal_woningen'),
		'bedrijven_aansluitingen': request.form.get('bedrijven_aansluitingen'),
		'huidige_stations': request.form.get('huidige_stations'),
		'benodigde_stations': request.form.get('benodigde_stations'),
		'om_te_bouwen_stations': request.form.get('om_te_bouwen_stations'),
		'kabel_type': request.form.get('kabel_type'),
		'kabel_hoeveelheid': request.form.get('kabel_hoeveelheid'),
		'station_type': request.form.get('station_type'),
		'uploaded_file': uploaded_file
	}

	return render_template('NETontwerp/resultaat.html', data=form_data)