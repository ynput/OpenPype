import React from 'react';
import classnames from 'classnames';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './styles.module.css';
import {
      PopupboxManager,
      PopupboxContainer
    } from 'react-popupbox';

const key_features = [
    {
        label: "Workfiles",
        description:
            "Save and load workfiles in progress. Change the context inside of the application.",
        docs: "/docs/artist_tools#workfiles",
    },
    {
        label: "Creator",
        description:
            "Universal GUI for defining content for publishing from your DCC app.",
        docs: "/docs/artist_tools#creator",
    },
    {
        label: "Loader",
        description:
            "Universal GUI for loading published assets into your DCC app.",
        docs: "/docs/artist_tools#loader",
    },
    {
        label: "Publisher",
        description:
            "Universal GUI for validating and publishng content from your DCC app.",
        image: "",
        docs: "/docs/artist_tools#publisher",
    },
    {
        label: "Scene manager",
        description:
            "Universal GUI for managing versions of assets loaded into your working scene.",
        docs: "docs/artist_tools#inventory",
      },
      {
          label: "Project manager",
          docs: "",
          description:
              "Tools for creating shots, assets and task within your project if you don't use third party project management",
      },
      {
        label: "Library Loader",
        description:
        "A loader GUI that allows yo to load content from dedicated cross project asset library",
        docs: "docs/artist_tools#library-loader",
        image: "",
    },
    {
        label: "Tray Publisher",
        link: "",
        description:
            "A standalone GUI for publishing data into pipeline without going though DCC app.",
        image: "",
    },
    {
        label: "App Launcher",
        link: "",
        description:
            "Standalone GUI for launching application in the chosen context directly from tray",
    },
    {
        label: "Configuration GUI",
        link: "",
        description:
            "All settings and configuration are done via openPype Settings tool. No need to dig around .json and .yaml",
    },
    {
        label: "Site Sync",
        docs: "docs/module_site_sync",
        description:
            "Built in file synchronization between your central storage (cloud or physical) and all your freelancers",
    },
    {
        label: "Timers Manager",
        link: "docs/admin_settings_system#timers-manager",
        description:
            "Service for monitoring the user activity to start, stop and synchronise time tracking.",
    },
    {
        label: "Farm rendering",
        docs: "docs/module_deadline",
        description:
            "Integrations with Deadline and Muster render managers. Render, publish and generate reviews on the farm.",
    },
    {
        label: "Remote",
        link: "",
        description:
            "Production proven in fully remote workflows. Pype can run of cloud servers and storage.",
    },
    {
        label: "Scene Builder",
        link: "",
        description:
            "System for simple scene building. Loads pre-defined publishes to scene with single click, speeding up scene preparation.",
    },
    {
        label: "Reviewables",
        docs: "docs/project_settings/settings_project_global#extract-review",
        description:
            "Generate automated reviewable quicktimes and sequences in any format, with metadata burnins.",
    },
];

const ftrack = [
  {
    docs: "docs/manager_ftrack_actions#applications",
    label: "App launchers",
    description: "Start any DCC application directly from ftrack task, with pype loaded."
  }, {
    docs: "docs/manager_ftrack#project-management",
    label: "Project Setup",
    description: "Quickly sets up project with customisable pre-defined structure and attributes."
  }, {
    docs: "docs/module_ftrack#update-status-on-task-action",
    label: "Automate statuses",
    description: "Quickly sets up project with customisable pre-defined structure and attributes."
  }, {
    docs: "docs/admin_ftrack#event-server",
    label: "Event Server",
    description: "Built-in ftrack event server takes care of all automation on your ftrack."
  }, {
    docs: "",
    label: "Review publishing",
    description: "All reviewables from all DCC aps, including farm renders are pushed to ftrack online review."
  }, {
    docs: "docs/admin_settings_system#timers-manager",
    label: "Auto Time Tracker",
    description: "Automatically starts and stops ftrack time tracker, base on artist activity."
  }
];

const ftrackActions = [
  {
    docbase: "docs/manager_ftrack_actions",
    label: "Launch Applications"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "RV Player"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "DJV view"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "Prepare Project"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "Delete Asset/Subset",
    target: "delete-assetsubset"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "Create Folders"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "Create Project Structure"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "Open File"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "Kill old jobs",
    target: "job-killer"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "Sort Review"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "Sync to Avalon"
  }, {
    docbase: "docs/manager_ftrack_actions#",
    label: "Propagate Thumbnails",
    target: "thumbnail"
  },
];


const maya_features = [

  {
    label: "Look Management",
    docs: "docs/artist_hosts_maya#look-development",
    description:"Publish shading networks with textures and assign them to all assets in the scene at once"
  },
  {
    label: "Project Shelves",
    description:"Add any custom projects scripts to dynamically generated maya shelves"
  },
  {
    label: "Playblasts",
    docs: "docs/artist_hosts_maya#reviews",
    description:"Makes all your playblasts consistent, with burnins and correct viewport settings"
  },
  {
    label: "Renderlayers and AOVs",
    description:"Full support of rendersetup layers and AOVs in all major renderers.",
    docs: "docs/artist_hosts_maya#working-with-pype-in-maya"
  },
  {
    label: "Farm Renders",
    description:"Send RenderSetup layers to the farm, generate quicktimes and publish multi-layer or individual AOVs.",
    docs: "docs/artist_hosts_maya#working-with-pype-in-maya"
  },
  {
    label: "Plugins Support",
    description:"OpenPYPE plays well with Arnold, Vray, Redshift and Yeti. With more plugins added upon client requests.",
    docs: "docs/artist_hosts_maya#working-with-yeti-in-pype"
  },
  {
    label: "Templated Build Workfile",
    description:"Build a workfile based on the task and project using a template designed by users.",
    docs: "docs/admin_hosts_maya#templated-build-workfile"
  }
]

const maya_families = [
    {label:"Model"},
    {label:"Look"},
    {label:"Rig"},
    {label:"Setdress"},
    {label:"Animation"},
    {label:"Cache"},
    {label:"VDB Cache"},
    {label:"Assembly"},
    {label:"Camera"},
    {label:"CameraRig"},
    {label:"RenderSetup"},
    {label:"Render"},
    {label:"Plate"},
    {label:"Review"},
    {label:"Workfile"},
    {label:".ASS StandIn"},
    {label:"Yeti Cache"},
    {label:"Yeti Rig"},
    {label:"Vray Scene"},
    {label:"Vray Proxy"},
]

const nuke_features = [

  {
    label: "Color Managed",
    description:"Fully colour managed outputs for work and review.",
    docs: "docs/artist_hosts_nuke#set-colorspace"
  }, {
    label: "Script Building",
    description:"Automatically build initial workfiles from published plates or renders",
    docs: "docs/artist_hosts_nuke#build-first-work-file"
  },
  {
    label: "Node Presets",
    description:"Template system for centrally controlled node parameters."
  },
  {
    label: "Rendering",
    description:"Support for local and farm renders, including baked reviews."
  },
  {
    label: "Slates",
    description:"Generate slates and attach them to rendered."
  }
]

const nuke_families = [
    {label: "Model"},
    {label: "Camera"},
    {label: "Render"},
    {label: "Plate"},
    {label: "Review"},
    {label: "Workfile"},
    {label: "LUT"},
    {label: "Gizmo"},
    {label: "Prerender"},
]

const deadline_features = [

  {
    label: "Tiled Renders",
    description:"Send high resolution tiled renders to deadline for single frames and sequences."
  },
  {
    label: "Maya",
    description:"Render maya rendersetup layers."
  },
  {
    label: "Nuke",
    description:"Render write nodes and generate review quicktimes with baked colours."
  },
  {
    label: "Harmony",
    description:"Render write nodes."
  },
  {
    label: "After Effects",
    description:"Render compositions."
  },
  {
    label: "Publishing",
    description:"All renders are automatically published. Generate reviewable quicktimes with optional burnins."
  }
]

const deadline_families = [
]

const hiero_features = [
  {
    label: "Project setup",
    description:"Automatic colour, timeline and fps setup of you hiero project."
  },
  {
    label: "Create shots",
    description:"Populate project with shots based on your conformed edit."
  },
  {
    label: "Publish plates",
    description:"Publish multiple tracks with plates to you shots from a single timeline."
  },
  {
    label: "Retimes",
    description:"Publish retime information for individual plates."
  },
  {
    label: "LUTS and fx",
    description:"Publish soft effects from your timeline to be used on shots."
  },
]

const hiero_families = [
    {label:"Render"},
    {label:"Plate"},
    {label:"Review"},
    {label:"LUT"},
    {label:"Nukenodes"},
    {label:"Gizmo"},
    {label:"Workfile"},
]

const blender_features = [

]

const blender_families = [
    {label:"Model"},
    {label:"Rig"},
    {label:"Setdress"},
    {label:"Layout"},
    {label:"Animation"},
    {label:"Point Cache"},
    {label:"Camera"},
    {label:"Workfile"},
]

const houdini_features = [

]

const houdini_families = [
    {label:"Model"},
    {label:"Point Cache"},
    {label:"VDB Cache"},
    {label:"Camera"},
    {label:"Workfile"},
]

const fusion_features = [

]

const fusion_families = [
    {label: "Render"},
    {label: "Plate"},
    {label: "Review"},
    {label: "Workfile"}
]

const harmony_families = [
    {label: "Render"},
    {label: "Plate"},
    {label: "Review"},
    {label: "Template"},
    {label: "Rig"},
    {label: "Palette"},
    {label: "Workfile"}
]

const tvpaint_families = [
    {label: "Render"},
    {label: "Review"},
    {label: "Image"},
    {label: "Audio"},
    {label: "Workfile"}
]

const photoshop_families = [
    {label: "Render"},
    {label: "Plate"},
    {label: "Image"},
    {label: "LayeredImage"},
    {label: "Background"},
    {label: "Workfile"}
]

const aftereffects_families = [
    {label: "Render"},
    {label: "Plate"},
    {label: "Image"},
    {label: "Audio"},
    {label: "Background"},
    {label: "Workfile"}
]


class FeatureKey extends React.Component {
  render() {
    const label = this.props.label
    const description = this.props.description
    const image = (this.props.image || "")
    const demo = (this.props.demo || "")
    const docs = (this.props.docs || "")
    return (
        <div className="card">
          <div class="card__image">
            {image != "" &&
            <img
              src={image}
              alt="Image alt text"
              title="Logo Title Text 1"
            />
            }
          </div>

          <div className="card__body">
            <h4>{label}</h4>
            <p>
              {description}
            </p>
          </div>
          <div className={classnames(
                                     "card__footer")}>

             <div class="button-group button-group--block">
               {demo != "" &&
                 <a href={demo} class="button button--secondary">Demo</a>
               }
               {docs != "" &&
                <a href={docs} class="button button--secondary">Docs</a>
               }
             </div>
          </div>
        </div>
    );
  }
}

class FeatureMedium extends React.Component {
  render() {
    const label = this.props.label
    const link = (this.props.link || "")
    const description = this.props.description
    const demo = (this.props.demo || "")
    const docs = (this.props.docs || "")
    return (
        <div className="card card_medium">
          <div className="card__header">
            <h4>{label}</h4>
          </div>
          <div className="card__body">
          <p>
            {description}
          </p>
          </div>
          <div className={classnames(
                                     "card__footer")}>
           <div class="button-group button-group--block">
             {demo != "" &&
               <a href={demo} class="button button--secondary">Demo</a>
             }
             {docs != "" &&
              <a href={docs} class="button button--secondary">Docs</a>
             }
           </div>
          </div>
        </div>
    );
  }
}

class FamilyCard extends React.Component {
  render() {
    const label = this.props.label
    const description = this.props.description
    const docbase = (this.props.docbase || "docs/artist_publish#")
    const target = (this.props.target || label).toLowerCase()

    return (
      <div className="card card_small">
        <a href={docbase + target.split(" ").join("-")}>
          <div className="card__body">
          <h5>{label}</h5>
          </div>
        </a>
      </div>
    );
  }
}



function Home() {
  const context = useDocusaurusContext();
  const {siteConfig = {}} = context;
  return (
    <Layout
      title={`${siteConfig.title}- Features`}
      description="Pype Feature list">


      <section className={classnames("section lightBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2>Key Features</h2>

          {key_features && key_features.length && (
            <div className={styles.card_box}>
              {key_features.map((props, idx) => (
                <FeatureKey key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>



      <section className={classnames("section darkBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2 id="ftrack">Ftrack</h2>

          {ftrack && ftrack.length && (
            <div className={styles.card_box}>
              {ftrack.map((props, idx) => (
                <FeatureMedium key={idx} {...props} />
              ))}
            </div>
          )}

          <h3> Actions and Events</h3>

          {ftrack && ftrack.length && (
            <div className={styles.card_box}>
              {ftrackActions.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className={classnames("section lightBackground")}>
        <div className={classnames(styles.card_container, "container")}>

          <h2 id="maya"><a href="docs/artist_hosts_blender">Autodesk Maya</a></h2>
          <p className="sectionDescription">versions 2017 and higher</p>

          <p>
            OpenPype includes very robust Maya implementation that can handle full CG workflow from model, 
            through animation till final renders. Scene settings, Your artists won't need to touch file browser at all and OpenPype will
            take care of all the file management. Most of maya workflows are supported including gpucaches, referencing, nested references and render proxies.
            </p>

          {maya_features && maya_features.length && (
            <div className={styles.card_box}>
              {maya_features.map((props, idx) => (
                <FeatureMedium key={idx} {...props} />
              ))}
            </div>
          )}

          <h3 className=""> Supported Families </h3>

          {maya_families && maya_families.length && (
            <div className={styles.card_box}>
              {maya_families.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className={classnames("section darkBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2 id="nuke"><a href="docs/artist_hosts_nuke">Foundry Nuke | NukeX</a></h2>

          <p className="sectionDescription">versions 11.0 and higher</p>

          {nuke_features && nuke_features.length && (
            <div className={styles.card_box}>
              {nuke_features.map((props, idx) => (
                <FeatureMedium key={idx} {...props} />
              ))}
            </div>
          )}

          <h3 className=""> Supported Families </h3>

          {nuke_families && nuke_families.length && (
            <div className={styles.card_box}>
              {nuke_families.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className={classnames("section lightBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2 id="hiero"><a href="docs/artist_hosts_blender">Foundry Hiero | Nuke Studio</a></h2>

          <p className="sectionDescription">versions 11.0 and higher</p>

          {hiero_features && hiero_features.length && (
            <div className={styles.card_box}>
              {hiero_features.map((props, idx) => (
                <FeatureMedium key={idx} {...props} />
              ))}
            </div>
          )}

          <h3 className=""> Supported Families </h3>

          {hiero_families && hiero_families.length && (
            <div className={styles.card_box}>
              {hiero_families.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className={classnames("section darkBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2><a href="docs/artist_hosts_photoshop">After Effects</a></h2>

          <p className="sectionDescription">versions 2020 and higher</p>

          <h3 className=""> Supported Families </h3>

          {aftereffects_families && aftereffects_families.length && (
            <div className={styles.card_box}>
              {aftereffects_families.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className={classnames("section lightBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2><a href="docs/artist_hosts_photoshop">Photoshop</a></h2>

          <p className="sectionDescription">versions 2020 and higher</p>

          <h3 className=""> Supported Families </h3>

          {photoshop_families && photoshop_families.length && (
            <div className={styles.card_box}>
              {photoshop_families.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className={classnames("section darkBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2><a href="docs/artist_hosts_harmony">Harmony</a></h2>

          <p className="sectionDescription">versions 17 and higher</p>

          <h3 className=""> Supported Families </h3>

          {harmony_families && harmony_families.length && (
            <div className={styles.card_box}>
              {harmony_families.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className={classnames("section lightBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2><a href="docs/artist_hosts_tvpaint">TV Paint</a></h2>

          <p className="sectionDescription">versions 11</p>

          <h3 className=""> Supported Families </h3>

          {tvpaint_families && tvpaint_families.length && (
            <div className={styles.card_box}>
              {tvpaint_families.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className={classnames("section darkBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2 id="houdini">Houdini</h2>

          <p className="sectionDescription">versions 16.0 and higher</p>

          <h3 className=""> Supported Families </h3>

          {houdini_families && houdini_families.length && (
            <div className={styles.card_box}>
              {houdini_families.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>


      <section className={classnames("section lightBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2><a href="docs/artist_hosts_blender">Blender</a></h2>

          <p className="sectionDescription">versions 2.83 and higher</p>

          <h3 className=""> Supported Families </h3>

          {blender_families && blender_families.length && (
            <div className={styles.card_box}>
              {blender_families.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>


      <section className={classnames("section darkBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2>Fusion</h2>

          <p className="sectionDescription">versions 9 and higher</p>

          <h3 className=""> Supported Families </h3>

          {fusion_families && fusion_families.length && (
            <div className={styles.card_box}>
              {fusion_families.map((props, idx) => (
                <FamilyCard key={idx} {...props} />
              ))}
            </div>
          )}
        </div>
      </section>


    </Layout>
    );
  }

  export default Home;
