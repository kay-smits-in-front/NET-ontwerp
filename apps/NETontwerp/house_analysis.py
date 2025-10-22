import cv2


def calculate_shape_properties(contour):
    """Calculate properties of a shape."""
    area = cv2.contourArea(contour)
    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    solidity = area / hull_area if hull_area > 0 else 0

    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0

    return {
        'area': area,
        'solidity': solidity,
        'aspect_ratio': aspect_ratio,
        'width': w,
        'height': h,
    }


def detect_houses_from_image(image_path):
    """Detect houses in uploaded image."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f'Could not load image from {image_path}')

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    params = {
        'min_area': 1500,
        'max_area': 100000,
        'min_solidity': 0.7,
        'max_aspect_ratio': 5.0,
    }

    house_shapes = []
    for contour in contours:
        props = calculate_shape_properties(contour)

        if props['area'] < params['min_area'] or props['area'] > params['max_area']:
            continue

        if props['solidity'] < params['min_solidity']:
            continue

        if props['aspect_ratio'] > params['max_aspect_ratio']:
            continue

        house_shapes.append(contour)

    return image, house_shapes


def draw_house_detections(image, house_shapes, output_path):
    """Draw detected houses and save result."""
    result = image.copy()
    for i, shape in enumerate(house_shapes):
        cv2.drawContours(result, [shape], 0, (0, 255, 0), 2)

        M = cv2.moments(shape)
        if M['m00'] != 0:
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            cv2.putText(
                result,
                str(i + 1),
                (cx, cy),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

    cv2.imwrite(str(output_path), result)
    return len(house_shapes)
