import avalon.unreal.pipeline as pipeline
import avalon.unreal.lib as lib
import unreal


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
    print("Starting rendering...")

    # Get selected sequences
    assets = unreal.EditorUtilityLibrary.get_selected_assets()

    # instances = pipeline.ls_inst()
    instances = [
        a for a in assets
        if a.get_class().get_name() == "AvalonPublishInstance"]

    inst_data = []

    for i in instances:
        data = pipeline.parse_container(i.get_path_name())
        if data["family"] == "render":
            inst_data.append(data)

    # subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    # queue = subsystem.get_queue()
    global queue
    queue = unreal.MoviePipelineQueue()

    for i in inst_data:
        job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
        job.sequence = unreal.SoftObjectPath(i["sequence"])
        job.map = unreal.SoftObjectPath(i["map"])
        job.author = "OpenPype"

        # User data could be used to pass data to the job, that can be read
        # in the job's OnJobFinished callback. We could, for instance, 
        # pass the AvalonPublishInstance's path to the job.
        # job.user_data = ""

        output_setting = job.get_configuration().find_or_add_setting_by_class(
            unreal.MoviePipelineOutputSetting)
        output_setting.output_resolution = unreal.IntPoint(1280, 720)
        output_setting.file_name_format = "{sequence_name}.{frame_number}"
        output_setting.output_directory.path += f"{i['subset']}/"

        renderPass = job.get_configuration().find_or_add_setting_by_class(
            unreal.MoviePipelineDeferredPassBase)
        renderPass.disable_multisample_effects = True

        job.get_configuration().find_or_add_setting_by_class(
            unreal.MoviePipelineImageSequenceOutput_PNG)

    # TODO: check if queue is empty

    global executor
    executor = unreal.MoviePipelinePIEExecutor()
    executor.on_executor_finished_delegate.add_callable_unique(
        _queue_finish_callback)
    executor.on_individual_job_finished_delegate.add_callable_unique(
        _job_finish_callback) # Only available on PIE Executor
    executor.execute(queue)
