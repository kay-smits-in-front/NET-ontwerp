import logging
import os

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
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


@bp.route('/map-extraction', methods=['GET'])
@handle_errors(redirect_endpoint='NETontwerp.main')
def map_extraction():
    """Interactive map-based house extraction interface"""
    return render_template('NETontwerp/map_extraction.html')


@bp.route('/api/extract-buildings', methods=['POST'])
@handle_errors(redirect_endpoint='NETontwerp.main')
def extract_buildings():
    """API endpoint to extract buildings within a polygon using Overpass API"""
    import requests
    from shapely.geometry import Point, Polygon
    from shapely.ops import transform
    import math

    def calculate_area_m2(building_poly, center_lat):
        """Calculate approximate area in square meters using local projection"""
        # Approximate meters per degree at given latitude
        meters_per_lat = 111320
        meters_per_lon = 111320 * math.cos(math.radians(center_lat))

        # Calculate area in square degrees then convert to m2
        area_deg = building_poly.area
        area_m2 = area_deg * meters_per_lat * meters_per_lon
        return abs(area_m2)

    def classify_house_type(area_m2, has_name, addr_housenumber):
        """Classify building into Dutch house types based on area and attributes"""
        # Filter out sheds and very small buildings
        if area_m2 < 50:
            return None

        # Buildings > 300m² are always bedrijf or flatgebouw
        if area_m2 > 300:
            return 'Bedrijf/Flatgebouw'

        # Buildings with names are bedrijven
        if has_name and has_name.strip():
            return 'Bedrijf'

        # Multiple house numbers = apartment complex
        if addr_housenumber and (',' in addr_housenumber or '-' in addr_housenumber):
            return 'Appartementencomplex'

        # Initial classification based on refined area ranges
        if 150 <= area_m2 <= 250:
            return 'Vrijstaand'  # Detached house
        elif 100 <= area_m2 <= 200:
            return 'Twee onder een kap'  # Semi-detached (needs validation later)
        elif 50 <= area_m2 <= 150:
            return 'Rijtjeshuis'  # Row house/terraced house
        else:
            # Outside typical ranges
            if area_m2 > 250:
                return 'Bedrijf/Flatgebouw'
            else:
                return 'Rijtjeshuis'  # Default to row house for small residential

    def buildings_are_adjacent(coords1, coords2, threshold=0.0001):
        """Check if two buildings share a boundary (are adjacent)"""
        poly1 = Polygon(coords1)
        poly2 = Polygon(coords2)

        # Check if polygons touch or are very close
        distance = poly1.distance(poly2)
        return distance < threshold

    def count_adjacent_buildings(building_idx, all_buildings):
        """Count how many buildings are adjacent to this building"""
        count = 0
        current_coords = all_buildings[building_idx]['coords']

        for idx, other_building in enumerate(all_buildings):
            if idx != building_idx:
                if buildings_are_adjacent(current_coords, other_building['coords']):
                    count += 1

        return count

    def get_adjacent_buildings(building_idx, all_buildings):
        """Get list of indices of buildings adjacent to this one"""
        adjacent = []
        current_coords = all_buildings[building_idx]['coords']

        for idx, other_building in enumerate(all_buildings):
            if idx != building_idx:
                if buildings_are_adjacent(current_coords, other_building['coords']):
                    adjacent.append(idx)

        return adjacent

    def is_near_road(building_center, roads, threshold=0.0005):
        """Check if building is near a road"""
        from shapely.geometry import LineString

        point = Point(building_center)

        for road in roads:
            if len(road) >= 2:
                line = LineString(road)
                if point.distance(line) < threshold:
                    return True

        return False

    try:
        data = request.get_json()
        polygon_coords = data.get('polygon', [])

        if len(polygon_coords) < 3:
            return jsonify({'error': 'Polygon moet minimaal 3 punten hebben'}), 400

        # Create bounding box for Overpass API query
        lats = [coord[0] for coord in polygon_coords]
        lngs = [coord[1] for coord in polygon_coords]
        bbox = f"{min(lats)},{min(lngs)},{max(lats)},{max(lngs)}"

        # Query Overpass API for buildings AND roads
        overpass_url = "http://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json][timeout:25];
        (
          way["building"]({bbox});
          relation["building"]({bbox});
          way["highway"]({bbox});
        );
        out body;
        >;
        out skel qt;
        """

        logger.info(f'Querying Overpass API with bbox: {bbox}')
        response = requests.post(overpass_url, data={'data': overpass_query}, timeout=30)
        response.raise_for_status()

        osm_data = response.json()
        logger.info(f'Received {len(osm_data.get("elements", []))} OSM elements')

        # Create polygon for intersection check
        poly = Polygon(polygon_coords)

        # Process data
        buildings = []
        roads = []
        nodes = {}
        total_area = 0

        # First pass: collect all nodes
        for element in osm_data.get('elements', []):
            if element['type'] == 'node':
                nodes[element['id']] = (element['lat'], element['lon'])

        # Second pass: collect roads
        for element in osm_data.get('elements', []):
            if element['type'] == 'way' and 'highway' in element.get('tags', {}):
                node_ids = element.get('nodes', [])
                road_coords = []
                for node_id in node_ids:
                    if node_id in nodes:
                        lat, lon = nodes[node_id]
                        road_coords.append([lat, lon])
                if len(road_coords) >= 2:
                    roads.append(road_coords)

        logger.info(f'Found {len(roads)} roads in area')

        # Third pass: process buildings
        for element in osm_data.get('elements', []):
            if element['type'] == 'way' and 'building' in element.get('tags', {}):
                node_ids = element.get('nodes', [])
                building_coords = []

                for node_id in node_ids:
                    if node_id in nodes:
                        lat, lon = nodes[node_id]
                        building_coords.append([lat, lon])

                if len(building_coords) >= 3:
                    # Check if building center is within polygon
                    building_poly = Polygon(building_coords)
                    center = building_poly.centroid

                    if poly.contains(Point(center.x, center.y)):
                        # Calculate area in square meters
                        area_m2 = calculate_area_m2(building_poly, center.x)

                        # Get building attributes
                        tags = element.get('tags', {})
                        has_name = tags.get('name', '')
                        addr_housenumber = tags.get('addr:housenumber', '')

                        # Initial classification
                        house_type = classify_house_type(area_m2, has_name, addr_housenumber)

                        # Only include actual houses (not bedrijven or flats yet)
                        if house_type and house_type not in ['Bedrijf', 'Bedrijf/Flatgebouw', 'Appartementencomplex']:
                            buildings.append({
                                'id': element['id'],
                                'coords': building_coords,
                                'center': [center.x, center.y],
                                'type': house_type,
                                'osm_type': tags.get('building', 'yes'),
                                'name': has_name,
                                'housenumber': addr_housenumber,
                                'area_m2': round(area_m2, 1),
                                'near_road': is_near_road([center.x, center.y], roads),
                            })

        logger.info(f'Found {len(buildings)} potential houses (before post-processing)')

        # Post-processing: refine house types based on adjacency and road proximity
        filtered_buildings = []

        for idx, building in enumerate(buildings):
            # Filter out buildings not near roads
            if not building['near_road']:
                logger.info(f'Filtering building {building["id"]} - not near road')
                continue

            # Count adjacent buildings
            adjacent_count = count_adjacent_buildings(idx, buildings)
            adjacent_indices = get_adjacent_buildings(idx, buildings)

            # If 3+ adjacent buildings, they are rijtjeshuizen
            if adjacent_count >= 3:
                building['type'] = 'Rijtjeshuis'
                building['adjacent_count'] = adjacent_count

            # Validate twee-onder-een-kap
            elif building['type'] == 'Twee onder een kap':
                # Must have exactly 1 adjacent building
                if adjacent_count == 1:
                    # Check if adjacent is also twee-onder-een-kap
                    adjacent_idx = adjacent_indices[0]
                    if buildings[adjacent_idx]['type'] == 'Twee onder een kap':
                        # Valid pair
                        building['adjacent_count'] = adjacent_count
                    else:
                        # Not a valid pair, reclassify as rijtjeshuis
                        building['type'] = 'Rijtjeshuis'
                        building['adjacent_count'] = adjacent_count
                else:
                    # Single twee-onder-een-kap doesn't exist, make it rijtjeshuis
                    building['type'] = 'Rijtjeshuis'
                    building['adjacent_count'] = adjacent_count

            else:
                building['adjacent_count'] = adjacent_count

            filtered_buildings.append(building)
            total_area += building['area_m2']

        logger.info(f'Found {len(filtered_buildings)} houses after filtering (roads + adjacency)')

        # Calculate total amperage (houses × 10A per house)
        total_amperage = len(filtered_buildings) * 10

        return jsonify({
            'success': True,
            'count': len(filtered_buildings),
            'buildings': filtered_buildings,
            'total_amperage': total_amperage,
            'total_area_m2': round(total_area, 1),
        })

    except requests.RequestException as e:
        logger.error(f'Overpass API error: {e}')
        return jsonify({'error': f'API fout: {str(e)}'}), 500
    except Exception as e:
        logger.error(f'Building extraction error: {e}')
        return jsonify({'error': f'Extractie fout: {str(e)}'}), 500
