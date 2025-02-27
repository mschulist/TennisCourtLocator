import glob
import math
import cv2 as cv
import numpy as np
from utilities import *
import os
import imutils

def cv_image_read(image_path):
    images = []
    temps = []
    for i in range(0, 360, 10):
        img = cv.imread(image_path)
        rotated = imutils.rotate(img, angle = i)
        for j in range(85, 118, 3):
            width = int(img.shape[0] * (j / 100))
            height = int(img.shape[1] * (j / 100))
            dim = (width, height)
            images.append(cv.resize(rotated, dim, interpolation = cv.INTER_AREA))

    
    for i in range(len(images)):
        temps.append(cv.cvtColor(images[i], cv.COLOR_BGR2GRAY))
    return temps


def find_tennis_court_template_matching(image):

    temp1 = cv.imread("./sample_courts/court1.png")
    temp1 = cv.cvtColor(temp1, cv.COLOR_BGR2GRAY) # bad code ik don't judge


    template = []

    for sample in glob.glob("./sample_courts/court*.png"): 
        template.extend(cv_image_read(sample))

    img_rgb = cv.imread(image)
    img_gray = cv.cvtColor(img_rgb, cv.COLOR_BGR2GRAY)

    name_parse = image[:-4].split("_")
    centerXCord = float(name_parse[1])
    centerYCord = float(name_parse[2])

    found_court = False
    for temp in template:
        w, h = temp1.shape[::-1]
        res = cv.matchTemplate(img_gray, temp, cv.TM_CCOEFF_NORMED)
        threshold = 0.67 # CHANGE LATER
        if np.max(res) >= threshold:
                print(np.max(res)) # for debugging and fun
        loc = np.where(res >= threshold)
        for pt in zip(*loc[::-1]):
            found_court = True
            cv.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)

    # git doesn't sync empty dirs
    if not os.path.exists("./labeled_images/"):
        os.mkdir("./labeled_images/")

    if found_court:
        labeled_file_name = "./labeled_images/" + str(centerXCord) + "_" + str(
            centerYCord) + "_" + "labeled.png"
        cv.imwrite(labeled_file_name, img_rgb)\

        return centerXCord, centerYCord, pt[0], pt[1]

    return None

def find_tennis_court_hough_analysis(image_filename):

    name_parse = image_filename[:-4].split("_")
    centerXCord = float(name_parse[1])
    centerYCord = float(name_parse[2])

    img_color = cv.imread(image_filename)
    img = cv.imread(image_filename, 0)
    cannyThres1 = 200
    cannyThres2 = 200
    edges = cv.Canny(img, cannyThres1, cannyThres2)
    rho = 1  # distance resolution in pixels of the Hough grid
    theta = np.pi / 180  # angular resolution in radians of the Hough grid
    threshold = 15  # minimum number of votes (intersections in Hough grid cell)
    min_line_length = 25  # minimum number of pixels making up a line
    max_line_gap = 12  # maximum gap in pixels between connectable line segments
    line_image = np.copy(img_color) * 0  # creating a blank to draw lines on
    lines = cv.HoughLinesP(edges, rho, theta, threshold, np.array([]),
                           min_line_length, max_line_gap)
    short_lines = []
    long_lines = []
    for line in lines:
        for x1, y1, x2, y2 in line:
            length = distance(x1, y1, x2, y2)
            angle = math.atan2(y2 - y1, x2 - x1)
            if angle > math.pi:
                angle = angle - math.pi
            if 40 < length < 55:
                short_lines.append((x1, y1, x2, y2, angle))
                # cv.line(line_image,(x1,y1),(x2,y2),(255,0,0), 1)
            elif 100 < length < 120:
                long_lines.append((x1, y1, x2, y2, angle))
                # cv.line(line_image,(x1,y1),(x2,y2),(255,0,0), 1)

    long_lines.sort(key=lambda x: x[4])

    count = 0
    adjacency = 10
    parallel_long_pairs = []
    for i in range(len(long_lines)):
        fx1, fy1, fx2, fy2, fangle = long_lines[i]
        for j in range(i + 1, min(len(long_lines), i + adjacency)):
            sx1, sy1, sx2, sy2, sangle = long_lines[j]
            # Check parallel
            if (abs(fangle - sangle) < math.pi / 30):
                count = count + 1
                # Check distance four possibilities
                firstDist = distance(fx1, fy1, sx1, sy1)
                secondDist = distance(fx1, fy1, sx2, sy2)
                thirdDist = distance(fx2, fy2, sx1, sy1)
                fourthDist = distance(fx2, fy2, sx2, sy2)
                if 40 < firstDist < 65 and 40 < fourthDist < 65:
                    # cv.line(line_image,(sx1,sy1),(sx2,sy2),(255,0,0), 1)
                    # cv.line(line_image, (fx1, fy1), (fx2, fy2), (255, 0, 0), 1)

                    parallel_long_pairs.append(
                        ((fx1, fy1), (sx1, sy1), (fx2, fy2), (sx2, sy2), fangle))
                elif 40 < secondDist < 65 and 40 < thirdDist < 65:
                    # cv.line(line_image, (sx1, sy1), (sx2, sy2), (255, 0, 0), 1)
                    # cv.line(line_image, (fx1, fy1), (fx2, fy2), (255, 0, 0), 1)
                    parallel_long_pairs.append(
                        ((fx1, fy1), (sx2, sy2), (fx2, fy2), (sx1, sy1), fangle))

    court_found = False
    for i in range(len(parallel_long_pairs)):
        (fx1, fy1), (sx1, sy1), (fx2, fy2), (sx2, sy2), long_angle = \
            parallel_long_pairs[i]

        # the first two connects, the last two connects
        firstConnector = None
        for shortx1, shorty1, shortx2, shorty2, angle in short_lines:
            # Check first pair

            if not -0.1 < math.cos(angle - long_angle) < 0.1:
                continue

            dist1 = distance(fx1, fy1, shortx1, shorty1)
            dist2 = distance(fx1, fy1, shortx2, shorty2)
            dist3 = distance(sx1, sy1, shortx1, shorty1)
            dist4 = distance(sx1, sy1, shortx2, shorty2)

            if dist1 < 15 and dist4 < 15:
                firstConnector = (shortx1, shorty1, shortx2, shorty2)
            elif dist2 < 15 and dist3 < 15:
                firstConnector = (shortx1, shorty1, shortx2, shorty2)

        if firstConnector == None:
            continue

        secondConnector = None
        for shortx1, shorty1, shortx2, shorty2, angle in short_lines:

            if not -0.1 < math.cos(angle - long_angle) < 0.1:
                continue

            dist1 = distance(fx2, fy2, shortx1, shorty1)
            dist2 = distance(fx2, fy2, shortx2, shorty2)
            dist3 = distance(sx2, sy2, shortx1, shorty1)
            dist4 = distance(sx2, sy2, shortx2, shorty2)

            if dist1 < 15 and dist4 < 15:
                secondConnector = (shortx1, shorty1, shortx2, shorty2)
            elif dist2 < 15 and dist3 < 15:
                secondConnector = (shortx1, shorty1, shortx2, shorty2)

        if secondConnector == None:
            continue

        cv.line(line_image, (firstConnector[0], firstConnector[1]),
                (firstConnector[2], firstConnector[3]), (255, 0, 0), 3)
        cv.line(line_image, (secondConnector[0], secondConnector[1]),
                (secondConnector[2], secondConnector[3]), (255, 0, 0), 3)
        cv.line(line_image, (fx1, fy1), (fx2, fy2), (255, 0, 0), 3)
        cv.line(line_image, (sx1, sy1), (sx2, sy2), (255, 0, 0), 3)

        court_found = True
        break

    if court_found:
        img = cv.imread(image_filename)
        lines_edges = cv.addWeighted(img, 0.8, line_image, 1, 0)
        labeled_file_name = "./labeled_images/" + str(centerXCord) + "_" + str(centerYCord) + "_" + "labeled.png"
        cv.imwrite(labeled_file_name, lines_edges)

        return centerXCord, centerYCord, firstConnector[0], firstConnector[1]

    return None

## Return a list of tuple coordinates
# [(centerXCord, centerYCord, pixelsX, pixelsY), (centerXCord, centerYCord, pixelsX, pixelsY) ...]
def find_tennis_court(list_of_images=None):
    imagepath = "./images/sateliteimage*.png"
    images = glob.glob(imagepath)

    result_list = []
    for image in images:

        print("Processing " + image)

        result = find_tennis_court_hough_analysis(image)

        if result is not None:
            result_list.append(result)
            continue

        result = find_tennis_court_template_matching(image)

        if result is not None:
            result_list.append(result)

    with_offsets = list(map(apply_offset_to_coordinates, result_list))

    final_dict_list = []

    for lat, lng in with_offsets:
        final_dict_list.append({"lat": lat, "lng": lng})

    return final_dict_list
