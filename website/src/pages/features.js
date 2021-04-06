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
    description: "Save and load workfiles in progress. Change the context inside of the application.",
    docs: "/docs/artist_tools#workfiles"
  }, {
    label: "Creator",
    description: "Universal GUI for defining content for publishing from your DCC app.",
    docs: "/docs/artist_tools#creator"
  }, {
    label: "Loader",
    description: "Universal GUI for loading published assets into your DCC app.",
    docs: "/docs/artist_tools#loader"
  }, {
    label: "Publisher",
    description: "Universal GUI for validating and publishng content from your DCC app.",
    image: "",
    docs: "/docs/artist_tools#publisher"
  }, {
    label: "Inventory",
    description: "Universal GUI for managing versions of assets loaded into your working scene.",
    docs: "docs/artist_tools#inventory",
  }, {
    label: "Library Loader",
    description: "A loader GUI that allows yo to load content from dedicated cross project asset library",
    docs: "docs/artist_tools#library-loader",
    image: ""
  }, {
    label: "Tray Publisher",
    link: "",
    description: "A standalone GUI for publishing data into pipeline without going though DCC app.",
    image: ""
  }, {
    label: "Pype Tray",
    link: "",
    description: "Cross platform wrapper app, which is the central point of pype. All other tools are ran from here."
  }, {
    label: "App Launcher",
    link: "",
    description: "Standalone GUI for launching application in the chosen context directly from tray"
  }, {
    label: "Timer Manager",
    link: "",
    description: "Service for monitoring the user activity to start, stop and synchronise time tracking."
  }, {
    label: "Farm rendering",
    link: "",
    description: "Integrations with Deadline and Muster render managers. Render, publish and generate reviews on the farm."
  }, {
    label: "Remote",
    link: "",
    description: "Production proven in fully remote workflows. Pype can run of cloud servers and storage."
  }
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
    docs: "docs/admin_ftrack#event-server",
    label: "Event Server",
    description: "Built-in ftrack event server takes care of all automation on your ftrack."
  }, {
    docs: "",
    label: "Review publishing",
    description: "All reviewables from all DCC aps, including farm renders are pushed to ftrack online review."
  }, {
    docs: "",
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
    label: "Model > Render",
    description:"We cover full project data flow from model throght animation, till final render.",
    docs: "docs/artist_hosts_maya#working-with-pype-in-maya"
  },
  {
    label: "Plugins Support",
    description:"Full support for Arnold, Vray, Redshift and Yeti. With more added upon client requests.",
    docs: "docs/artist_hosts_maya#working-with-yeti-in-pype"
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
    description:"Automatically build first workfiles from published plates or renders",
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
    {label: "Group"},
    {label: "Workfile"},
    {label: "LUT"},
    {label: "Cache"},
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
    description:"Render maya scenes ."
  },
  {
    label: "Nuke",
    description:"Template system for centrally controlled node parameters."
  },
  {
    label: "Vray Standalone",
    description:"Support for local and farm renders, including baked reviews."
  },
  {
    label: "Publishing",
    description:"Generate slates and attach them to rendered."
  }
]

const deadline_families = [
]

const hiero_features = [
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
    {label:"RenderSetup"},
    {label:"Render"},
    {label:"Review"},
    {label:"Workfile"},
]

const houdini_features = [

]

const houdini_families = [
    {label:"Model"},
    {label:"Point Cache"},
    {label:"VDB Cache"},
    {label:"Camera"},
    {label:"Review"},
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
    {label: "Pallete"},
    {label: "Workfile"}
]

const photoshop_families = [
    {label: "Render"},
    {label: "Plate"},
    {label: "Image"},
    {label: "LayeredImage"},
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

          <h2 id="maya">Autodesk Maya</h2>
          <p className="sectionDescription">versions 2017 and higher</p>

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
          <h2 id="nuke">Foundry Nuke | NukeX</h2>

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
          <h2 id="hiero">Foundry Hiero | Nuke Studio</h2>

          <p className="sectionDescription">versions 11.0 and higher</p>

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
          <h2>Blender</h2>

          <p className="sectionDescription">versions 2.80 and higher</p>

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


      <section className={classnames("section lightBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2>Harmony</h2>

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


      <section className={classnames("section darkBackground")}>
        <div className={classnames(styles.card_container, "container")}>
          <h2>Photoshop</h2>

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


    </Layout>
    );
  }

  export default Home;
