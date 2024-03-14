# 3DE4.script.name:	~Import Sequance

# 3DE4.script.version:	v1.1

# 3DE4.script.gui:	Main Window::AromaOpenPype

# 3DE4.script.comment:	Automated script for importing sequences.
# 3DE4.script.comment:	Author: Eslam Ezzat
# 3DE4.script.comment:	v1.0 @ 23 Jan 2024

# v1.1 updated by Eslam Ezzat 25 Jan 2024 (fetch the metadeta of exr and asssign them)

import os
import tde4
import subprocess
import xml.etree.ElementTree as et
import pandas as pd
from openpype.pipeline import install_host, is_installed
from openpype.hosts.equalizer.api import EqualizerHost
from openpype.tools.utils import host_tools


def install_3de_host():
    print("Running AYON integration ...")
    install_host(EqualizerHost())


if not is_installed():
    install_3de_host()

def getMetaData(camera_id, lens_id):

    frame = tde4.getCurrentFrame(camera_id)
    frame_path = tde4.getCameraFrameFilepath(camera_id, frame)
    try:
        xml = tde4.convertOpenEXRMetaDataToXML(frame_path)
    except:
        print("File '" + frame_path + "' doesn't seem to be an EXR file.")
        return

    root = et.fromstring(xml)
    metadata_attrs = dict()
    for a in root.findall("attribute"):
        name = a.find("name").text
        value = a.find("value").text
        if name and value: metadata_attrs[name] = value

    # Assign the metadata attributes into Camera
    if 'camera_fps' in metadata_attrs:
        tde4.setCameraFPS(camera_id, float(metadata_attrs['camera_fps']))

    # Assign the metadata attributes into Lens
    if 'camera_focal' in metadata_attrs:
        camera_focal = metadata_attrs['camera_focal'].split()
        if camera_focal[1] == 'mm':
            tde4.setLensFocalLength(lens_id, float(camera_focal[0])/10)
        else:
            tde4.setLensFocalLength(lens_id, float(camera_focal[0]))

    # Set filmback
    df = pd.read_csv("D://test_dir//camera_dataset.csv")
    def cantain(x, y):
        return y.upper() in x.upper()
    def get_col(name, check):
        return df[name].apply(lambda x: cantain(x, check))

    cam_name = 'None'
    cam_format = "prores"
    cam_resolution = "hd"
    if 'cameraModel' in metadata_attrs:
        cam_name = metadata_attrs['cameraModel']

    filmback_h = df[(get_col('name', cam_name)) & (get_col('format', cam_format)) & (get_col('resolution', cam_resolution))].filmback_height
    filmback_h = list(filmback_h)
    if filmback_h:
        tde4.setLensFBackHeight(lens_id, float(filmback_h[0])/10)


def createNewSequence(file_path):

    tde4.newProject()
    camera_id = tde4.getCurrentCamera()
    lens_id = tde4.getCameraLens(camera_id)

    image_dir, image_path = os.path.split(file_path)
    image_name, id, image_format = image_path.split(".")
    pattern = ".".join([image_name, len(id)*"#", image_format])
    path = os.path.join(image_dir, pattern)

    images = os.listdir(image_dir) # [ActionVFX_v01.1002.exr, ActionVFX_v01.1003.exr]
    images.sort()

    total_frames_list = []
    pattern_split = pattern.split(".") # [ActionVFX_v01, ####, exr]
    for image in images:
        image_split = image.split(".") # [ActionVFX_v01, 1002, exr]
        if pattern_split[0] == image_split[0] and len(pattern_split) == len(image_split):
            # name == name and lenth == lenth
            total_frames_list.append(image_split[1])

    # Auto assign camera attributes
    start_frame = int(min(total_frames_list))
    end_frame = int(max(total_frames_list))
    len_frames = len(total_frames_list)

    tde4.setCameraSequenceAttr(camera_id, start_frame, end_frame, 1)
    tde4.setCameraName(camera_id, image_name)
    tde4.setCameraPath(camera_id, path)
    tde4.setCameraFrameOffset(camera_id, start_frame)
    tde4.setCamera8BitColorGamma(camera_id, 2.2 if image_format == 'exr' else 1)
    tde4.setCameraPlaybackRange(camera_id,1,len_frames)

    # Set lens distortion model
    film_aspect = float(tde4.getLensFilmAspect(lens_id))
    if film_aspect > 2:
        tde4.setLensLDModel(lens_id, "3DE4 Anamorphic - Standard, Degree 4")

    # Get the MetaData of the current frame
    getMetaData(camera_id, lens_id)

    # Import Buffer Compression if exists or Exprot it
    # Performace -> Image Cache -> Store Comperssion File -> in Sequence Directory.
    Buffer_path = os.path.join(image_dir, '.'.join([image_name, 'x', image_format, '3de_bcompress']))
    if os.path.exists(Buffer_path):
        tde4.importBufferCompressionFile(camera_id)

    else:
        gamma		 = tde4.getCamera8BitColorGamma(camera_id)
        softclip	 = tde4.getCamera8BitColorSoftclip(camera_id)
        black, white = tde4.getCamera8BitColorBlackWhite(camera_id)

        command = 'makeBCFile.exe -source %s -start %s -end %s -out %s -black %f -white %f -gamma %f -softclip %f'%(tde4.getCameraPath(camera_id),start_frame,end_frame,image_dir,black,white,gamma,softclip)
        tde4.postProgressRequesterAndContinue("Export Fast Buffer Compression File...", "Please wait...",100,"Ok")
        try:
            for i in range(33):
                tde4.updateProgressRequester(i,'Exporting: %s'%tde4.getCameraName(camera_id))
            process = subprocess.Popen(command, shell=True)
            process.wait()
        except:
            raise Exception('there is an error in the command')
        for i in range(33, 101):
            tde4.updateProgressRequester(i,'Exporting: %s'%tde4.getCameraName(camera_id))
        tde4.importBufferCompressionFile(camera_id)
        tde4.unpostProgressRequester()

if __name__ == "__main__":

    path = tde4.postFileRequester("<AROMA> Please Select First Frame Of Sequence...", "*")
    # path = "D:\\test_dir\\v001\\alf01_ep03_sc0002_sh0030_pl01_v001.1001.exr"
    if path:
        createNewSequence(path)
