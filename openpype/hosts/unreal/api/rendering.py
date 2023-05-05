import os

import unreal

from openpype.settings import get_project_settings
from openpype.pipeline import Anatomy
from openpype.hosts.unreal.api import pipeline
from openpype.widgets.message_window import Window


queue = None
executor = None


def _queue_finish_callback(exec, success):
    unreal.log("Render completed. Success: " + str(success))

    # Delete our reference so we don't keep it alive.
    global executor
    global queue
    del executor
    del queue


def _job_finish_callback(job, success):
    # You can make any edits you want to the editor world here, and the world
    # will be duplicated when the next render happens. Make sure you undo your
    # edits in OnQueueFinishedCallback if you don't want to leak state changes
    # into the editor world.
    unreal.log("Individual job completed.")


def start_rendering():
    """
    Start the rendering process.
    """
    unreal.log("Starting rendering...")

    # Get selected sequences
    assets = unreal.EditorUtilityLibrary.get_selected_assets()

    if not assets:
        Window(
            parent=None,
            title="No assets selected",
            message="No assets selected. Select a render instance.",
            level="warning")
        raise RuntimeError(
            "No assets selected. You need to select a render instance.")

    # instances = pipeline.ls_inst()
    instances = [
        a for a in assets
        if a.get_class().get_name() == "AyonPublishInstance"]

    inst_data = []

    for i in instances:
        data = pipeline.parse_container(i.get_path_name())
        if data["family"] == "render":
            inst_data.append(data)

    try:
        project = os.environ.get("AVALON_PROJECT")
        anatomy = Anatomy(project)
        root = anatomy.roots['renders']
    except Exception as e:
        raise Exception(
            "Could not find render root in anatomy settings.") from e

    render_dir = f"{root}/{project}"

    # subsystem = unreal.get_editor_subsystem(
    #     unreal.MoviePipelineQueueSubsystem)
    # queue = subsystem.get_queue()
    global queue
    queue = unreal.MoviePipelineQueue()

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    data = get_project_settings(project)
    config = None
    config_path = str(data.get("unreal").get("render_config_path"))
    if config_path and unreal.EditorAssetLibrary.does_asset_exist(config_path):
        unreal.log("Found saved render configuration")
        config = ar.get_asset_by_object_path(config_path).get_asset()

    for i in inst_data:
        sequence = ar.get_asset_by_object_path(i["sequence"]).get_asset()

        sequences = [{
            "sequence": sequence,
            "output": f"{i['output']}",
            "frame_range": (
                int(float(i["frameStart"])),
                int(float(i["frameEnd"])) + 1)
        }]
        render_list = []

        # Get all the sequences to render. If there are subsequences,
        # add them and their frame ranges to the render list. We also
        # use the names for the output paths.
        for seq in sequences:
            subscenes = pipeline.get_subsequences(seq.get('sequence'))

            if subscenes:
                for sub_seq in subscenes:
                    sequences.append({
                        "sequence": sub_seq.get_sequence(),
                        "output": (f"{seq.get('output')}/"
                                   f"{sub_seq.get_sequence().get_name()}"),
                        "frame_range": (
                            sub_seq.get_start_frame(), sub_seq.get_end_frame())
                    })
            else:
                # Avoid rendering camera sequences
                if "_camera" not in seq.get('sequence').get_name():
                    render_list.append(seq)

        # Create the rendering jobs and add them to the queue.
        for render_setting in render_list:
            job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
            job.sequence = unreal.SoftObjectPath(i["master_sequence"])
            job.map = unreal.SoftObjectPath(i["master_level"])
            job.author = "Ayon"

            # If we have a saved configuration, copy it to the job.
            if config:
                job.get_configuration().copy_from(config)

            # User data could be used to pass data to the job, that can be
            # read in the job's OnJobFinished callback. We could,
            # for instance, pass the AyonPublishInstance's path to the job.
            # job.user_data = ""

            output_dir = render_setting.get('output')
            shot_name = render_setting.get('sequence').get_name()

            settings = job.get_configuration().find_or_add_setting_by_class(
                unreal.MoviePipelineOutputSetting)
            settings.output_resolution = unreal.IntPoint(1920, 1080)
            settings.custom_start_frame = render_setting.get("frame_range")[0]
            settings.custom_end_frame = render_setting.get("frame_range")[1]
            settings.use_custom_playback_range = True
            settings.file_name_format = f"{shot_name}" + ".{frame_number}"
            settings.output_directory.path = f"{render_dir}/{output_dir}"

            job.get_configuration().find_or_add_setting_by_class(
                unreal.MoviePipelineDeferredPassBase)

            render_format = data.get("unreal").get("render_format", "png")

            if render_format == "png":
                job.get_configuration().find_or_add_setting_by_class(
                    unreal.MoviePipelineImageSequenceOutput_PNG)
            elif render_format == "exr":
                job.get_configuration().find_or_add_setting_by_class(
                    unreal.MoviePipelineImageSequenceOutput_EXR)
            elif render_format == "jpg":
                job.get_configuration().find_or_add_setting_by_class(
                    unreal.MoviePipelineImageSequenceOutput_JPG)
            elif render_format == "bmp":
                job.get_configuration().find_or_add_setting_by_class(
                    unreal.MoviePipelineImageSequenceOutput_BMP)

    # If there are jobs in the queue, start the rendering process.
    if queue.get_jobs():
        global executor
        executor = unreal.MoviePipelinePIEExecutor()

        preroll_frames = data.get("unreal").get("preroll_frames", 0)

        settings = unreal.MoviePipelinePIEExecutorSettings()
        settings.set_editor_property(
            "initial_delay_frame_count", preroll_frames)

        executor.on_executor_finished_delegate.add_callable_unique(
            _queue_finish_callback)
        executor.on_individual_job_finished_delegate.add_callable_unique(
            _job_finish_callback)  # Only available on PIE Executor
        executor.execute(queue)
