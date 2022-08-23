# -*- coding: utf-8 -*-
"""Python wrapper for RoyalRender XML job file."""
from xml.dom import minidom as md
import attr
from collections import namedtuple, OrderedDict


CustomAttribute = namedtuple("CustomAttribute", ["name", "value"])


@attr.s
class RRJob:
    """Mapping of Royal Render job file to a data class."""

    # Required
    # --------

    # Name of your render application. Same as in the render config file.
    # (Maya, Softimage)
    Software = attr.ib()  # type: str

    # The OS the scene was created on, all texture paths are set on
    # that OS. Possible values are windows, linux, osx
    SceneOS = attr.ib()  # type: str

    # Renderer you use. Same as in the render config file
    # (VRay, Mental Ray, Arnold)
    Renderer = attr.ib()  # type: str

    # Version you want to render with. (5.11, 2010, 12)
    Version = attr.ib()  # type: str

    # Name of the scene file with full path.
    SceneName = attr.ib()  # type: str

    # Is the job enabled for submission?
    # enabled by default
    IsActive = attr.ib()  # type: str

    # Sequence settings of this job
    SeqStart = attr.ib()  # type: int
    SeqEnd = attr.ib()  # type: int
    SeqStep = attr.ib()  # type: int
    SeqFileOffset = attr.ib()  # type: int

    # If you specify ImageDir, then ImageFilename has no path. If you do
    # NOT specify ImageDir, then ImageFilename has to include the path.
    # Same for ImageExtension.
    # Important: Do not forget any _ or . in front or after the frame
    # numbering. Usually ImageExtension always starts with a . (.tga, .exr)
    ImageDir = attr.ib()  # type: str
    ImageFilename = attr.ib()  # type: str
    ImageExtension = attr.ib()  # type: str

    # Some applications always add a . or _ in front of the frame number.
    # Set this variable to that character. The user can then change
    # the filename at the rrSubmitter and the submitter keeps
    # track of this character.
    ImagePreNumberLetter = attr.ib()  # type: str

    # If you render a single file, e.g. Quicktime or Avi, then you have to
    # set this value. Videos have to be rendered at once on one client.
    ImageSingleOutputFile = attr.ib(default="false")  # type: str

    # Semi-Required (required for some render applications)
    # -----------------------------------------------------

    # The database of your scene file. In Maya and XSI called "project",
    # in Lightwave "content dir"
    SceneDatabaseDir = attr.ib(default=None)  # type: str

    # Required if you want to split frames on multiple clients
    ImageWidth = attr.ib(default=None)  # type: int
    ImageHeight = attr.ib(default=None)  # type: int
    Camera = attr.ib(default=None)  # type: str
    Layer = attr.ib(default=None)  # type: str
    Channel = attr.ib(default=None)  # type: str

    # Optional
    # --------

    # Used for the RR render license function.
    # E.g. If you render with mentalRay, then add mentalRay. If you render
    # with Nuke and you use Furnace plugins in your comp, add Furnace.
    # TODO: determine how this work for multiple plugins
    RequiredPlugins = attr.ib(default=None)  # type: str

    # Frame Padding of the frame number in the rendered filename.
    # Some render config files are setting the padding at render time.
    ImageFramePadding = attr.ib(default=None)  # type: str

    # Some render applications support overriding the image format at
    # the render commandline.
    OverrideImageFormat = attr.ib(default=None)  # type: str

    # rrControl can display the name of additonal channels that are
    # rendered. Each channel requires these two values. ChannelFilename
    # contains the full path.
    ChannelFilename = attr.ib(default=None)  # type: str
    ChannelExtension = attr.ib(default=None)  # type: str

    # A value between 0 and 255. Each job gets the Pre ID attached as small
    # letter to the main ID. A new main ID is generated for every machine
    # for every 5/1000s.
    PreID = attr.ib(default=None)  # type: int

    # When the job is received by the server, the server checks for other
    # jobs send from this machine. If a job with the PreID was found, then
    # this jobs waits for the other job. Note: This flag can be used multiple
    # times to wait for multiple jobs.
    WaitForPreID = attr.ib(default=None)  # type: int

    # List of submitter options per job
    # list item must be of `SubmitterParameter` type
    SubmitterParameters = attr.ib(factory=list)  # type: list

    # List of Custom job attributes
    # Royal Render support custom attributes in format <CustomFoo> or
    # <CustomSomeOtherAttr>
    # list item must be of `CustomAttribute` named tuple
    CustomAttributes = attr.ib(factory=list)  # type: list

    # Additional information for subsequent publish script and
    # for better display in rrControl
    UserName = attr.ib(default=None)  # type: str
    CustomSeQName = attr.ib(default=None)  # type: str
    CustomSHotName = attr.ib(default=None)  # type: str
    CustomVersionName = attr.ib(default=None)  # type: str
    CustomUserInfo = attr.ib(default=None)  # type: str
    SubmitMachine = attr.ib(default=None)  # type: str
    Color_ID = attr.ib(default=2)  # type: int

    RequiredLicenses = attr.ib(default=None)  # type: str

    # Additional frame info
    Priority = attr.ib(default=50)  # type: int
    TotalFrames = attr.ib(default=None)  # type: int
    Tiled = attr.ib(default=None)  # type: str


class SubmitterParameter:
    """Wrapper for Submitter Parameters."""
    def __init__(self, parameter, *args):
        # type: (str, list) -> None
        self._parameter = parameter
        self._values = args

    def serialize(self):
        # type: () -> str
        """Serialize submitter parameter as a string value.

        This can be later on used as text node in job xml file.

        Returns:
            str: concatenated string of parameter values.

        """
        return '"{param}={val}"'.format(
            param=self._parameter, val="~".join(self._values))


@attr.s
class SubmitFile:
    """Class wrapping Royal Render submission XML file."""

    # Syntax version of the submission file.
    syntax_version = attr.ib(default="6.0")  # type: str

    # Delete submission file after processing
    DeleteXML = attr.ib(default=1)  # type: int

    # List of submitter options per job
    # list item must be of `SubmitterParameter` type
    SubmitterParameters = attr.ib(factory=list)  # type: list

    # List of job is submission batch.
    # list item must be of type `RRJob`
    Jobs = attr.ib(factory=list)  # type: list

    @staticmethod
    def _process_submitter_parameters(parameters, dom, append_to):
        # type: (list[SubmitterParameter], md.Document, md.Element) -> None
        """Take list of :class:`SubmitterParameter` and process it as XML.

        This will take :class:`SubmitterParameter`, create XML element
        for them and convert value to Royal Render compatible string
        (options and values separated by ~)

        Args:
            parameters (list of SubmitterParameter): List of parameters.
            dom (xml.dom.minidom.Document): XML Document
            append_to (xml.dom.minidom.Element): Element to append to.

        """
        for param in parameters:
            if not isinstance(param, SubmitterParameter):
                raise AttributeError(
                    "{} is not of type `SubmitterParameter`".format(param))
            xml_parameter = dom.createElement("SubmitterParameter")
            xml_parameter.appendChild(dom.createTextNode(param.serialize()))
            append_to.appendChild(xml_parameter)

    def serialize(self):
        # type: () -> str
        """Return all data serialized as XML.

        Returns:
            str: XML data as string.

        """
        def filter_data(a, v):
            """Skip private attributes."""
            if a.name.startswith("_"):
                return False
            if v is None:
                return False
            return True

        root = md.Document()
        # root element: <RR_Job_File syntax_version="6.0">
        job_file = root.createElement('RR_Job_File')
        job_file.setAttribute("syntax_version", self.syntax_version)

        # handle Submitter Parameters for batch
        # <SubmitterParameter>foo=bar~baz~goo</SubmitterParameter>
        self._process_submitter_parameters(
            self.SubmitterParameters, root, job_file)

        for job in self.Jobs:  # type: RRJob
            if not isinstance(job, RRJob):
                raise AttributeError(
                    "{} is not of type `SubmitterParameter`".format(job))
            xml_job = root.createElement("Job")
            # handle Submitter Parameters for job
            self._process_submitter_parameters(
                job.SubmitterParameters, root, xml_job
            )
            job_custom_attributes = job.CustomAttributes

            serialized_job = attr.asdict(
                job, dict_factory=OrderedDict, filter=filter_data)
            serialized_job.pop("CustomAttributes")
            serialized_job.pop("SubmitterParameters")

            for custom_attr in job_custom_attributes:  # type: CustomAttribute
                serialized_job["Custom{}".format(
                    custom_attr.name)] = custom_attr.value

            for item, value in serialized_job.items():
                xml_attr = root.create(item)
                xml_attr.appendChild(
                    root.createTextNode(value)
                )
                xml_job.appendChild(xml_attr)

        return root.toprettyxml(indent="\t")
