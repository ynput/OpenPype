import re
import os.path
import copy
import shutil
import pyblish.api
import xml.etree.ElementTree
from glob import glob
from datetime import datetime


# noinspection DuplicatedCode
def parse_cdl(path):
    with open(path, "r") as f:
        cdl_data = f.read().lower()

    cdl = {}

    slope_pattern = r"<slope>(?P<sR>[-,\d,.]*)[ ]{1}(?P<sG>[-,\d,.]+)[ ]{1}(?P<sB>[-,\d,.]*)</slope>"
    offset_pattern = r"<offset>(?P<oR>[-,\d,.]*)[ ]{1}(?P<oG>[-,\d,.]+)[ ]{1}(?P<oB>[-,\d,.]*)</offset>"
    power_pattern = r"<power>(?P<pR>[-,\d,.]*)[ ]{1}(?P<pG>[-,\d,.]+)[ ]{1}(?P<pB>[-,\d,.]*)</power>"
    sat_pattern = r"<saturation\>(?P<sat>[-,\d,.]+)</saturation\>"
    path_pattern = r"<originalpath\>(?P<path>.*)<\/originalpath\>"

    slope_match = re.search(slope_pattern, cdl_data)
    if slope_match:
        slope = (tuple(map(float, (slope_match.group("sR"), slope_match.group("sG"), slope_match.group("sB")))))
        cdl["slope"] = slope

    offset_match = re.search(offset_pattern, cdl_data)
    if offset_match:
        offset = (tuple(map(float, (offset_match.group("oR"), offset_match.group("oG"), offset_match.group("oB")))))
        cdl["offset"] = offset

    power_match = re.search(power_pattern, cdl_data)
    if power_match:
        power = (tuple(map(float, (power_match.group("pR"), power_match.group("pG"), power_match.group("pB")))))
        cdl["power"] = power

    sat_match = re.search(sat_pattern, cdl_data)
    if sat_match:
        sat = float(sat_match.group("sat"))
        cdl["sat"] = sat

    path_match = re.search(path_pattern, cdl_data)
    if path_match:
        path_value = path_match.group("path")
        cdl["file"] = path_value

    return cdl


def format_xml(root):
    dom = xml.dom.minidom.parseString(xml.etree.ElementTree.tostring(root))
    xml_doc = dom.toprettyxml(indent="\t")

    return xml_doc


def write_xml(root, dst=""):
    xml_doc = format_xml(root)
    with open(dst, "w") as xml_file:
        xml_file.write(xml_doc)

    print("ccc file written -> {}".format(dst))


def resolve_id(edit):
    shot_name = os.path.basename(edit["file"]).rsplit(".", 1)[0]
    id_ = shot_name

    return id_


def root_xml():
    ccc = xml.etree.ElementTree.Element("ColorCorrectionCollection")

    return ccc


def cc_xml(id_, cdl):
    cc = xml.etree.ElementTree.Element("ColorCorrection")
    cc.attrib = {"id": str(id_)}
    sop_node = xml.etree.ElementTree.Element("SOPNode")
    slope = xml.etree.ElementTree.Element("Slope")
    offset = xml.etree.ElementTree.Element("Offset")
    power = xml.etree.ElementTree.Element("Power")
    sat_node = xml.etree.ElementTree.Element("SatNode")
    sat = xml.etree.ElementTree.Element("Saturation")
    og_path_node = xml.etree.ElementTree.Element("OriginalPath")

    # Set SOPS values
    slope.text = "{0} {1} {2}".format(cdl["slope"][0], cdl["slope"][1], cdl["slope"][2])
    offset.text = "{0} {1} {2}".format(cdl["offset"][0], cdl["offset"][1], cdl["offset"][2])
    power.text = "{0} {1} {2}".format(cdl["power"][0], cdl["power"][1], cdl["power"][2])
    sat.text = str(cdl["sat"])
    og_path_node.text = cdl["file"]

    # Add SOPS relationships
    cc.append(sop_node)
    sop_node.append(slope)
    sop_node.append(offset)
    sop_node.append(power)
    cc.append(sat_node)
    sat_node.append(sat)
    cc.append(og_path_node)

    return cc


def ccc_xml(cdls, limit=""):
    # CCC files are a collection of CDLs which means that support for more than one CDL is required
    # Hence why there is iteration through cdls
    if isinstance(cdls, dict):
        cdls = [cdls]
    ccc = root_xml()
    cc = None

    # Can not have an id that was used in the same CCC file
    used_ids = []
    for event, cdl in enumerate(cdls):
        if not (cdl["slope"] and cdl["offset"] and cdl["power"] and cdl["sat"]):
            print("Skipping CDL {}".format(event))

        if not cdl.get("id"):
            id_ = resolve_id(cdl)
            if id_ in used_ids:
                id_ += str(event+1)

            if not id_ in limit and limit:
                print("EDL cdl {0} -> Skipping because not in limit {1}".format(id_, limit))
                continue
        else:
            id_ = cdl.get("id")

        used_ids.append(id_)

        cc = cc_xml(id_, cdl)
        ccc.append(cc)

    if not cc:
        print("No SOPS to convert")
        return False

    return ccc


def ccc_breakout_xml(cdl, limit=""):
    ccc = root_xml()
    cc = None

    if not (cdl["slope"] and cdl["offset"] and cdl["power"] and cdl["sat"]):
        print("Skipping edl event {}".format(cdl["name"]))

    if not cdl.get("id"):
        id_ = resolve_id(cdl)
    else:
        id_ = cdl.get("id")

    if not id_ in limit and limit:
        print("EDL CDL {0} -> Skipping because not in limit {1}".format(id_, limit))
        return False

    cc = cc_xml(id_, cdl)
    ccc.append(cc)

    if not cc:
        print("No SOPS to convert")
        return False, ""

    return ccc, str(id_)


def create_backup_grade(grade):
    """
    Backups are timestamped relative to when they were packaged backup this way we can have more history
    Each grade is in the same history folder. this is not a hidden folder
    """
    ocio_path = os.path.dirname(grade)
    history_path = ocio_path + "/history"
    if not os.path.isdir(history_path):
        os.mkdir(history_path)

    current_time = datetime.now()
    base, seperator, extension = os.path.basename(grade).rpartition(".")
    backup_grade = "{0}/{1}_{2}{3}{4}".format(
        history_path,
        base,
        current_time.strftime("%Y%m%d_%H%M%S"),
        seperator,
        extension
    )
    backup_grade_result = shutil.move(grade, backup_grade)

    return backup_grade_result


def same_grade(cdl, cdl_path):
    """Test whether two cdls have the same values"""
    match_cdl = parse_cdl(cdl_path)
    if (
            cdl.get("slope") == match_cdl.get("slope") and
            cdl.get("offset") == match_cdl.get("offset") and
            cdl.get("power") == match_cdl.get("power") and
            cdl.get("sat") == match_cdl.get("sat") and
            cdl.get("file") == match_cdl.get("file")
        ):
        return True
    else:
        return False

def sort_by_descript(item):
    """Sort is done by giving a value to the alpha part of the plate name description and adding an integer for plate number"""
    plate_prefix_order = ("pl", "bg", "e", "fg")
    id_, grade = item
    grade_name = os.path.basename(grade).lower().rsplit(".", 1)[0]
    descriptor = grade_name.split("_")[-1]
    descript_num_split = re.split("(\d+)",descriptor)
    if not len(descript_num_split) > 1:
        descript_num_split.append(0)
    alpha = descript_num_split[0]
    num = int(descript_num_split[-2]) if descript_num_split[-2].isdigit() else 0
    descriptor_value = plate_prefix_order.count(alpha)*10+num

    return descriptor_value


def  get_main_grade(ocio_directory):
    """Determine if Grade file is meant to be main grade or it if it is an element grade"""
    original_grades = []
    for grade in glob(ocio_directory + "/*"):
        if os.path.isfile(grade) and not os.path.basename(grade) == "grade.ccc" and (
                grade.endswith(".ccc") or
                grade.endswith(".cdl") or
                grade.endswith(".cc")
            ):
            original_grades.append((os.path.basename(parse_cdl(grade)["file"]).rsplit(".")[0], grade))

    if len(original_grades) == 1:
        return original_grades[0][1]

    # Testing to see if there is a high chance that main grade is only shot name
    possible_main = sorted(original_grades, key=lambda x: len(x[0]))[0]
    for name, grade in original_grades:
        # If a grades name is in the other grades name it is for sure the main grade
        if name == possible_main[0]:
            continue
        if not possible_main[0] in name:
            break
    else:
        return possible_main[1]

    # Use description sorting method
    descript_grade = sorted(original_grades, key=sort_by_descript)[0]

    return descript_grade[1]


class IntegrateColorFile(pyblish.api.InstancePlugin):
    """Integrate Color File for plate."""

    order = pyblish.api.IntegratorOrder
    label = "Integrate Color File"
    families = ["plate"]

    def process(self, instance):
        if instance.data.get("cdl"):
            cdl = instance.data["cdl"]
        else:
            self.log.warning("No CDL found in instance data")
            return

        temp_extension = "tmp"
        template_data = copy.deepcopy(instance.data["anatomyData"])
        template_data["ext"] = temp_extension
        anatomy = instance.context.data["anatomy"]
        anatomy_filled = anatomy.format(template_data)
        publish_dir = anatomy_filled["publish"]["folder"]
        publish_file = anatomy_filled["publish"]["file"]
        version = anatomy_filled["publish"]["version"]
        shot_root = publish_dir.split("/publish/")[0]
        grade_name = publish_file.replace("_{0}.{1}".format(version, temp_extension), ".ccc")

        ocio_directory = "{0}/ocio/grade".format(shot_root)
        grade_path = ocio_directory + "/" + grade_name
        plate_grades = glob(ocio_directory+"/*")
        main_grade_path = ocio_directory + "/" + "grade.ccc"

        self.log.info("Ensuring shot OCIO dir exists: {0}".format(ocio_directory))
        if not os.path.exists(ocio_directory):
            self.log.info("OCIO dir did not exist. Making directory")
            os.makedirs(ocio_directory)

        skip_write = False
        if grade_path in plate_grades:
            # Grade previously copied. Test to see if unique CDL data and if so then backup previous file and make new plate CDL
            if same_grade(cdl, grade_path):
                skip_write = True
                # Run main_grade and figure out which grade should be main
            else:
                backup_grade = create_backup_grade(grade_path)
                self.log.info("New grade is unique. Creating backup grade: {}".format(backup_grade))

        if not skip_write:
            if cdl["file"].rsplit(".", 1)[-1] in ("3dl", "cube"):
                self.log.critical('3D Luts are not supported currently')
                pass
                # shutil.move()
            else:
                ccc_file = ccc_xml(cdl)
                write_xml(ccc_file, grade_path)
                self.log.info("Writing CDL to OCIO Grade folder: {}".format(grade_path))

        main_grade = get_main_grade(ocio_directory)
        if os.path.islink(main_grade_path):
            os.unlink(main_grade_path)

        os.symlink(main_grade, main_grade_path)
        self.log.info("Creating Grade.ccc symlink to: {}".format(os.path.basename(main_grade)))
