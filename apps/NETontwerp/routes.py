import logging
import os

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from core.error_handler import handle_errors

logger = logging.getLogger(__name__)
bp = Blueprint('NETontwerp', __name__, url_prefix='/NETontwerp')


def allowed_file(filename):
    allowed = ['png', 'jpg', 'jpeg', 'pdf']
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def ensure_upload_folder():
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        logger.info(f'Created upload folder: {upload_folder}')


@bp.route('/')
def main():
    return render_template(
        'NETontwerp/NETontwerp.html',
        title='NETontwerp',
        data={'message': 'Welkom bij NETontwerp!'},
    )


@bp.route('/house-detection', methods=['GET', 'POST'])
@handle_errors(redirect_endpoint='NETontwerp.main')
def house_detection():
    if request.method == 'POST':
        return handle_house_detection_upload()

    return render_template('NETontwerp/house_detection_upload.html')


@bp.route('/street-assignment', methods=['GET', 'POST'])
@handle_errors(redirect_endpoint='NETontwerp.house_detection')
def street_assignment():
    if request.method == 'POST':
        return handle_street_assignment()

    house_count = session.get('house_count', 0)
    detection_image = session.get('detection_image')

    if not house_count:
        flash('Geen huizen gedetecteerd. Upload eerst een screenshot.', 'error')
        return redirect(url_for('NETontwerp.house_detection'))

    cable_types = get_cable_types()

    return render_template(
        'NETontwerp/street_assignment.html',
        house_count=house_count,
        detection_image=detection_image,
        cable_types=cable_types,
    )


def handle_house_detection_upload():
    ensure_upload_folder()

    if 'screenshot' not in request.files:
        flash('Geen bestand geüpload', 'error')
        return redirect(url_for('NETontwerp.house_detection'))

    file = request.files['screenshot']
    if file.filename == '':
        flash('Geen bestand geselecteerd', 'error')
        return redirect(url_for('NETontwerp.house_detection'))

    if not allowed_file(file.filename):
        flash('Alleen PNG, JPG en JPEG bestanden zijn toegestaan', 'error')
        return redirect(url_for('NETontwerp.house_detection'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        from apps.NETontwerp.house_analysis import (
            detect_houses_from_image,
            draw_house_detections,
        )

        image, house_shapes = detect_houses_from_image(filepath)

        detection_filename = f'detection_{filename}'
        detection_filepath = os.path.join(
            current_app.config['UPLOAD_FOLDER'], detection_filename
        )

        house_count = draw_house_detections(image, house_shapes, detection_filepath)

        session['house_count'] = house_count
        session['detection_image'] = detection_filename
        session['original_image'] = filename

        logger.info(f'Detected {house_count} houses in {filename}')

        return redirect(url_for('NETontwerp.street_assignment'))

    except Exception as e:
        logger.error(f'Error detecting houses: {e}')
        flash(f'Fout bij detectie: {str(e)}', 'error')
        return redirect(url_for('NETontwerp.house_detection'))


def handle_street_assignment():
    street_names_input = request.form.get('street_names', '')
    street_names = [s.strip() for s in street_names_input.split(',') if s.strip()]

    if not street_names:
        flash('Voer minimaal één straatnaam in', 'error')
        return redirect(url_for('NETontwerp.street_assignment'))

    house_count = session.get('house_count', 0)
    houses_per_street = house_count // len(street_names)

    cable_assignments = {}
    for street in street_names:
        cable_type = request.form.get(f'cable_{street}')
        if cable_type:
            cable_assignments[street] = cable_type

    street_data = []
    total_connected = 0

    for street in street_names:
        cable = cable_assignments.get(street)
        houses_in_street = houses_per_street
        ampere_needed = houses_in_street * 10
        kva_needed = ampere_needed * 0.23

        if cable:
            cable_capacity = get_cable_capacity(cable)
            can_handle = cable_capacity >= ampere_needed
            connected = houses_in_street if can_handle else 0
            total_connected += connected
        else:
            can_handle = False
            connected = 0

        street_data.append(
            {
                'name': street,
                'houses': houses_in_street,
                'ampere_needed': ampere_needed,
                'kva_needed': round(kva_needed, 2),
                'cable': cable,
                'can_handle': can_handle,
                'connected': connected,
            }
        )

    result_data = {
        'total_houses': house_count,
        'total_streets': len(street_names),
        'houses_per_street': houses_per_street,
        'total_connected': total_connected,
        'total_unconnected': house_count - total_connected,
        'streets': street_data,
        'detection_image': session.get('detection_image'),
    }

    return render_template('NETontwerp/cable_assignment_result.html', data=result_data)


def get_cable_types():
    return [
        {'name': '4*240mm2 Al', 'capacity': 240},
        {'name': '4*150mm2 Al (basis)', 'capacity': 150},
        {'name': '4*95mm2 Al', 'capacity': 95},
        {'name': '4*50mm2 Al', 'capacity': 50},
        {'name': '4*16mm2 Cu', 'capacity': 70},
        {'name': '4*6mm2 Cu', 'capacity': 30},
    ]


def get_cable_capacity(cable_name):
    cables = get_cable_types()
    for cable in cables:
        if cable['name'] == cable_name:
            return cable['capacity']
    return 0


@bp.route('/berekening', methods=['GET', 'POST'])
@handle_errors(redirect_endpoint='NETontwerp.main')
def berekening():
    if request.method == 'POST':
        return handle_form_submission()

    cable_types = [c['name'] for c in get_cable_types()]

    station_types = [
        'pacto 10 tot 400 kva',
        'pacto 20 tot 630kva (most preferred)',
        'pacto 25 tot 630 kva maximaal 1000Ampere',
        'akagkps3 tot 630kva',
        'Batenburg tot 630kva',
        'diabolo tot 630kva',
    ]

    return render_template(
        'NETontwerp/berekeningen.html',
        cable_types=cable_types,
        station_types=station_types,
    )


def handle_form_submission():
    ensure_upload_folder()

    uploaded_file = None
    if 'pdf_file' in request.files:
        file = request.files['pdf_file']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_file = filename
            logger.info(f'File uploaded: {filename}')
        elif file and file.filename != '':
            flash('Alleen PDF bestanden zijn toegestaan', 'error')
            return redirect(url_for('NETontwerp.berekening'))

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
        'uploaded_file': uploaded_file,
    }

    return render_template('NETontwerp/resultaat.html', data=form_data)
