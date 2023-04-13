import re
import os.path
import copy
import json
import shutil
import pyblish.api
import xml.etree.ElementTree
from glob import glob
from datetime import datetime
import opentimelineio as otio

LUTS_3D = ["cube", "3dl", "csp", "lut"]
LUTS_2D = ["ccc", "cc", "cdl"]

# EDL is not by nature a color file nor a LUT. For this reason it's seperated from previous categories
COLOR_FILE_EXTS = LUTS_2D + LUTS_3D + ["edl"]


def parse_edl_events(path, color_edits_only=False):
    """
    EDL is parsed using OTIO and then placed into a data struture for output "edl"
    Data is stored under the understanding that it will be used for identifying plate names which are linked to CDLs

    EDL LOC metadata is parsed with OTIO under markers and then regexed to find the main bit of information which
    will link it to a plate name further down the line

    Underscores are not counted ({0,}) but are left greedy incase naming doesn't follow normal shot convention
    but instead follows plate pull naming convention.
    Example: abc_101_010_010_element
    Example: abc_101_010_010_element_fire

    Examples of targeted matches:
    abc_101_010_010_element
    abc_101_010_010
    abc_101_010
    101_010_010

    Examples of what does not match:
    abc_101
    101_001
    _abc_101_010
    abc_101_010_
    """
    shot_pattern = r"(?<!_)(?P<LOC>[a-zA-Z0-9]{3,4}_((?<=_)[a-zA-Z0-9]{3,4}_){1,2}[a-zA-Z0-9]{3,4}(?<!_)(_[a-zA-Z0-9]{1,}){0,})\b"

    # ignore_timecode_mismatch is set to True to ensure that OTIO doesn't get confused by
    # TO CLIP NAME and FROM CLIP NAME timecode ranges
    timeline = otio.adapters.read_from_file(path, ignore_timecode_mismatch=True)

    if len(timeline.tracks) > 1:
        raise Exception("EDL can not contain more than one track. Something went wrong")

    edl = {"events": {}}

    # There is a possibility that the entry count doesn't start at 1.
    # However it's extremely rare and it's purpose is to keep track of order
    entry_count = 0
    for clip in timeline.tracks[0].each_child():
        if isinstance(clip, otio.schema.Clip):
            entry_count += 1
            loc_value = ""
            tape_value = ""
            entry = {"clip_name": clip.name}
            if clip.metadata.get("cdl"):
                cdl = clip.metadata["cdl"]
                entry.update(
                    {
                        "slope": tuple(cdl["asc_sop"]["slope"]),
                        "offset": tuple(cdl["asc_sop"]["offset"]),
                        "power": tuple(cdl["asc_sop"]["power"]),
                        "sat": cdl.get("asc_sat") or 1.0,
                    }
                )
            else:
                if color_edits_only:
                    continue

            if clip.markers:
                # Join markers (*LOC). The data is strictly being stored to parse shot name
                # Space is added to make parsing much easier and predictable
                full_clip_loc = " ".join([" "] + [m.name for m in clip.markers])
                loc_match = re.search(shot_pattern, full_clip_loc)
                loc_value = loc_match.group("LOC") if loc_match else ""

            # Capture tape and source name
            if clip.metadata.get("cmx_3600"):
                if clip.metadata["cmx_3600"].get("reel"):
                    tape_value = clip.metadata["cmx_3600"].get("reel")
                # No need for source name? If matches clip name and clip name is more intentional?
                # if clip.metadata("cmx_3600").get("comments"):
                #     for comment in clip.metadata("cmx_3600").get("comments"):
                #         if "source file" in comment.lower():
                #             source_file_value = comment.split(":", 1)[-1].strip()
                #             break

            entry.update(
                {
                    "tape": tape_value,
                    "LOC": loc_value,
                }
            )
            edl["events"][str(entry_count)] = entry

    # Finish EDL info
    edl["first_entry"] = 1
    edl["last_entry"] = entry_count

    return edl


def parse_cdl(path):
    with open(path, "r") as f:
        cdl_data = f.read().lower()

    slope_pattern = r"<slope>(?P<sR>[-,\d,.]*)[ ]{1}(?P<sG>[-,\d,.]+)[ ]{1}(?P<sB>[-,\d,.]*)</slope>"
    offset_pattern = r"<offset>(?P<oR>[-,\d,.]*)[ ]{1}(?P<oG>[-,\d,.]+)[ ]{1}(?P<oB>[-,\d,.]*)</offset>"
    power_pattern = r"<power>(?P<pR>[-,\d,.]*)[ ]{1}(?P<pG>[-,\d,.]+)[ ]{1}(?P<pB>[-,\d,.]*)</power>"
    sat_pattern = r"<saturation\>(?P<sat>[-,\d,.]+)</saturation\>"

    slope_match = re.search(slope_pattern, cdl_data)
    slope = (tuple(map(float, (slope_match.group("sR"), slope_match.group("sG"), slope_match.group("sB"))))) \
        if slope_match else None

    offset_match = re.search(offset_pattern, cdl_data)
    offset = (tuple(map(float, (offset_match.group("oR"), offset_match.group("oG"), offset_match.group("oB"))))) \
        if offset_match else None

    power_match = re.search(power_pattern, cdl_data)
    power = (tuple(map(float, (power_match.group("pR"), power_match.group("pG"), power_match.group("pB"))))) \
        if power_match else None

    sat_match = re.search(sat_pattern, cdl_data)
    sat = float(sat_match.group("sat")) if sat_match else None

    cdl = {
        "slope": slope,
        "offset": offset,
        "power": power,
        "sat": sat,
        "file": path,
    }

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
                id_ += str(event + 1)

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
        history_path, base, current_time.strftime("%Y%m%d_%H%M%S"), seperator, extension
    )
    backup_grade_result = shutil.move(grade, backup_grade)

    return backup_grade_result


def same_grade(color_path, grade_path, color_type, cdl={}):
    """Test whether two color files have the same values"""
    if color_type == "edl":
        match_cdl = parse_cdl(grade_path)
        if (
            cdl.get("slope") == match_cdl.get("slope")
            and cdl.get("offset") == match_cdl.get("offset")
            and cdl.get("power") == match_cdl.get("power")
            and cdl.get("sat") == match_cdl.get("sat")
            and cdl.get("file") == match_cdl.get("file")
        ):
            return True
        else:
            return False
    else:
        with open(color_path, "r") as color_file, open(grade_path, "r") as grade_file:
            return color_file.read() == grade_file.read()


def sort_by_descript(item):
    """Sort is done by giving a value to the alpha part of the plate name description and adding an integer for plate number"""
    plate_prefix_order = ("pl", "bg", "e", "fg")
    id_, grade = item
    grade_name = os.path.basename(grade).lower().rsplit(".", 1)[0]
    descriptor = grade_name.split("_")[-1]
    descript_num_split = re.split("(\d+)", descriptor)
    if not len(descript_num_split) > 1:
        descript_num_split.append(0)
    alpha = descript_num_split[0]
    num = int(descript_num_split[-2]) if descript_num_split[-2].isdigit() else 0
    descriptor_value = plate_prefix_order.count(alpha) * 10 + num

    return descriptor_value


class IngestMeta:
    """
    Meta is stored in the following format:
    filename:{
        "source_path":"path/to/file.ccc"
        "plate":"associated_plate_name"
    },
    Here is a sample json file with ingest meta
    {
        "101_001_010.ccc":{
            "source_path":"/proj/zzz/incoming/20210202/101_001_010/101_001_010.ccc"
            "plate":"101_001_010_bg1"
            "main_grade":True,
        },
    }

    Built out of multiple filename entries with pertaining meta
    main_grade is needed to be able to determine if there was a custom set grade.ccc link
    """

    basename = "color_ingest_meta.json"
    metadata = {}
    historic_main_grade = ""

    def __init__(self, ocio_directory):
        self.ocio_directory = ocio_directory
        self.meta_path = os.path.join(ocio_directory, self.basename)
        self.main_grade_file = os.path.join(ocio_directory, "grade.ccc")
        self.get_ingest_meta()

    def get_ingest_meta(self):
        if os.path.isfile(self.meta_path):
            # Read the JSON file back into a Python object
            with open(self.meta_path, "r") as f:
                data = json.load(f)
            self.metadata = data
            self.historic_main_grade = self.get_meta_main_grade()
        else:
            # Leave meta as is if meta does not exist on disk
            return

    def write_ingest_meta(self):
        meta_dir = os.path.dirname(self.meta_path)
        if not os.path.isdir(meta_dir):
            os.makedirs(meta_dir)

        with open(self.meta_path, "w") as f:
            json.dump(self.metadata, f)

    def get_meta_main_grade(self):
        for filename in self.metadata:
            # New entries won't have main_grade attribute
            if "main_grade" in self.metadata[filename]:
                if self.metadata[filename]["main_grade"]:
                    return filename

        return False

    def set_meta_main_grade(self, target_grade):
        for filename in self.metadata:
            # target_grade can be empty depending on if there was a main grade set or not
            if not filename == target_grade:
                self.metadata[filename]["main_grade"] = False
            else:
                self.metadata[filename]["main_grade"] = True

    def add_grade(self, filename, source_path, plate):
        """Main grade is not determined at this point"""

        self.metadata[filename] = {
            "source_path": source_path,
            "plate": plate,
        }

    def remove_grade(self, filename):
        if filename in self.metadata:
            del self.metadata[filename]

    def get_main_grade(self):
        """
        If main grade is out of line as in someone manually changed it then set all grades to False
        Under that case the target_filename will be empty ""
        """

        # Don't need to store when grade was modified. if grade was modified it would be recored by this same logic previously
        if os.path.isfile(self.main_grade_file):
            main_grade_mtime = os.path.getmtime(self.main_grade_file)
            main_grade_exists = True
        else:
            main_grade_exists = False

        if os.path.isfile(self.meta_path):
            ingest_meta_mtime = os.path.getmtime(self.meta_path)
            ingest_meta_exists = True
        else:
            ingest_meta_exists = False

        # Historic main grade is useful when there is ingest_meta.
        # If there is no ingest_meta use grade.ccc as the key logic
        set_grade = False
        if main_grade_exists and ingest_meta_exists:
            # If ingest_meta_mtime is greater AND historic main grade
            # We know that since ingest_meta_exists that there will be valid historic_main_grade
            if main_grade_mtime < ingest_meta_mtime and self.historic_main_grade:
                set_grade = True

        elif main_grade_exists and not ingest_meta_exists:
            # When grade is found and not ingest_meta we can assume
            # there was custom link performed
            # Test to see whether there is a valid color file linked
            if not os.path.isfile(os.path.realpath(self.main_grade_file)):
                set_grade = True

        else:
            # There are only two other conditions which will always be True
            # If not ingest and not grade.
            # AND
            # If ingest and not grade.
            set_grade = True

            # If there are grades that are not in the ingest meta json still use those grades as potential main grades?

        # Add conditional for if shot name from shot folder is in grade name and if not then push prio to end of list

        if set_grade:
            """Determine if Grade file is meant to be main grade or if it is an element grade"""
            original_grades = [(f.rsplit(".", 1)[0], f) for f in self.metadata.keys()]

            if len(original_grades) == 1:
                main_grade = original_grades[0][1]
                return main_grade

            # Testing to see if there is a high chance that main grade is only shot name
            possible_main = sorted(original_grades, key=lambda x: len(x[0]))[0]
            for name, grade in original_grades:
                # If a grades name is in the other grades name it is for sure the main grade
                if name == possible_main[0]:
                    continue
                if not possible_main[0] in name:
                    break
            else:
                main_grade = possible_main[1]
                return possible_main[1]

            # Use description sorting method
            main_grade = sorted(original_grades, key=sort_by_descript)[0][1]
            return main_grade


class IntegrateColorFile(pyblish.api.InstancePlugin):
    """Integrate Color File for plate."""

    order = pyblish.api.IntegratorOrder
    label = "Integrate Color File"
    families = ["plate"]

    optional = True

    def process(self, instance):
        if instance.data.get("shot_grade"):
            color_info = instance.data["shot_grade"]
            ignore = color_info["ignore"]
            if ignore:
                self.log.info("Skipping plate color ingest. Ignore grade was set")
                return
            color_path = color_info["path"]
            color_type = color_info["type"]
        else:
            self.log.warning("No color info found in instance data")
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
        plate_name = publish_file.replace("_{0}.{1}".format(version, temp_extension), "")

        ocio_directory = "{0}/ocio/grade".format(shot_root)
        grade_path = os.path.join(ocio_directory, os.path.basename(color_path))
        plate_grades = glob(ocio_directory + "/*")
        main_grade_path = os.path.join(ocio_directory, "grade.ccc")

        self.log.info("Ensuring shot OCIO dir exists: {0}".format(ocio_directory))
        if not os.path.exists(ocio_directory):
            self.log.info("OCIO dir did not exist. Making directory")
            os.makedirs(ocio_directory)

        skip_write = False
        backup_grade = ""
        if grade_path in plate_grades:
            # Grade previously copied. Test to see if unique CDL data and if so then backup previous file and make new plate CDL
            # When checking if same grade - test whether file is exactly the same instead of values
            if same_grade(color_path, grade_path, color_type, cdl=color_info.get("cdl")):
                skip_write = True
                self.log.info("New grade already matches a grade in shot OCIO directory")
                # Run main_grade and figure out which grade should be main
            else:
                backup_grade = create_backup_grade(grade_path)
                self.log.info("New grade is unique. Creating backup grade: {}".format(backup_grade))

        if not skip_write:
            if color_info["type"] == "edl":
                ccc_file = ccc_xml(color_info["cdl"])
                write_xml(ccc_file, grade_path)
                self.log.info("Writing CDL to OCIO Grade folder: {}".format(grade_path))
            else:
                shutil.copyfile(color_path, grade_path)

        # Create color ingest meta on disk
        ingest_meta = IngestMeta(ocio_directory)

        # Make sure that backup grade is removed from ingest_meta before adding grade
        # Could rely on filename being the same and dict key overwrite but same grade doesn't always have same name
        if backup_grade:
            ingest_meta.remove_grade(os.path.dirname(main_grade))

        ingest_meta.add_grade(os.path.basename(color_path), color_path, plate_name)

        main_grade = ingest_meta.get_main_grade()
        ingest_meta.set_meta_main_grade(main_grade)
        # Create symlink for main grade
        if main_grade:
            if os.path.islink(main_grade_path):
                os.unlink(main_grade_path)

            os.symlink(main_grade, main_grade_path)
            self.log.info("Creating Grade.ccc symlink to: {}".format(os.path.basename(main_grade)))
        else:
            self.log.info(
                "Main Grade modified by user and left as is: {}".format(
                    os.path.basename(os.path.realpath(main_grade_path))
                )
            )

        ingest_meta.write_ingest_meta()
        self.log.info("Ingest meta writen out")
