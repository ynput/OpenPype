try:
    from openpype.lib import Logger
    from openpype.pipeline.publish.lib import remote_publish
except ImportError as exc:
    # Ensure Deadline fails by output an error that contains "Fatal Error:"
    raise ImportError("Fatal Error: %s" % exc)


if __name__ == "__main__":
    # Perform remote publish with thorough error checking
    log = Logger.get_logger(__name__)
    remote_publish(log)
