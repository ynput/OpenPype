import React from 'react';
import classnames from 'classnames';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './styles.module.css';

import {BadgesSection} from '../components';

const services = [
  {
    title: <>Training</>,
    description: (
      <>
        From helping your TDs and production managers to complete on-site Ftrack and workflow training.
      </>
    ),
  },
  {
    title: <>Consulting</>,
    description: (
      <>
        An outside, independent point of view. We’ll work with you on all fronts to get your productions running smoothly.
      </>
    ),
  },
  {
    title: <>Support</>,
    description: (
      <>
        Experience and time is what we are selling. Whether you want to deploy our open source tools or you need a bespoke solution.
      </>
    ),
  },
  {
    title: <>Coding</>,
    description: (
      <>
        We build an open, peer-reviewed pipeline, which can be shared across studios to reduce the cost and speed up the development.
      </>
    ),
  },
];

const collab = [
  {
    title: 'Kredenc Studio',
    image: '/img/kredenc.png',
    infoLink: 'http://kredenc.studio'
  }, {
    title: 'Bumpybox',
    image: '/img/bumpybox_bw.png',
    infoLink: 'http://bumpybox.com'
  }, {
    title: 'Colorbleed',
    image: '/img/colorbleed_logo.png',
    infoLink: 'http://colorbleed.nl'
  }, {
    title: 'Moonshine',
    image: '/img/moonshine_logotype.png',
    infoLink: 'https://www.moonshine.tw/'
  }, {
    title: 'Avalon',
    image: '/img/avalon_logotype.png',
    infoLink: 'https://getavalon.github.io/2.0/'
  }
];

const clients = [
  {
    title: 'Imagine Studio',
    image: '/img/imagine_logo.png',
    infoLink: 'https://imaginestudio.cz/'
  }, {
    title: 'Dazzle Pictures',
    image: '/img/dazzle_CB.png',
    infoLink: 'https://www.dazzlepictures.net/'
  }, {
    title: 'Fresh Films',
    image: '/img/fresh-films-logo.jpg',
    infoLink: 'http://freshfilms.cz/'
  }, {
    title: '3DE',
    image: '/img/3de.png',
    infoLink: 'https://www.3de.com.pl/'
  }, {
    title: 'Cubic Motion',
    image: '/img/cubicmotion.png',
    infoLink: 'https://cubicmotion.com/'
  }, {
    title: 'Clothcat Animation',
    image: '/img/clothcat.png',
    infoLink: 'https://www.clothcatanimation.com/'
  }, {
    title: 'Incognito',
    image: '/img/client_incognito.png',
    infoLink: 'https://incognito.studio/'
  }, {
    title: 'Bionaut Animation',
    image: '/img/bionaut_logo.png',
    infoLink: 'https://bionaut.cz/'
  }, {
    title: '3Bohemians',
    image: '/img/3bohemians-logo.png',
    infoLink: 'https://www.3bohemians.eu//'
  }, {
    title: 'Fourth Wall Animation',
    image: '/img/client_fourthwall_logo.png',
    infoLink: 'https://fourthwallanimation.com/'
  }, {
    title: 'The Scope Studio',
    image: '/img/thescope_logo.png',
    infoLink: 'https://thescope.studio/'
  }, {
    title: 'The Line Animation',
    image: '/img/thelineanimationlogo.png',
    infoLink: 'https://www.thelineanimation.com/'
  }, {
    title: 'Krutart Animation',
    image: '/img/client_krutart_logo.png',
    infoLink: 'https://krutart.cz/'
  }, {
    title: 'Filmmore',
    image: '/img/filmmore_logotype_bw.png',
    infoLink: 'https://filmmore.nl/'
  },
  {
    title: 'Yowza Animation',
    image: '/img/client_yowza_logo.png',
    infoLink: 'https://yowzaanimation.com/'
  },

];

function Service({imageUrl, title, description}) {
  const imgUrl = useBaseUrl(imageUrl);
  return (
    <div className={classnames('col col--3', styles.feature)}>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

function Client({title, image, infoLink}) {
  const imgUrl = useBaseUrl(image);
  return (
    <a className="client" href={infoLink}>
      <img src={image} alt="" title={title}></img>
    </a>
  );
}

function Collaborator({title, image, infoLink}) {
  const imgUrl = useBaseUrl(image);
  return (
    <a className="collab" href={infoLink}>
      <img src={image} alt="" title={title}></img>
    </a>
  );
}

function Home() {
  const context = useDocusaurusContext();
  const {siteConfig = {}} = context;
  return (
    <Layout
      title={`${siteConfig.title}- code.training.support`}
      description="Description will go into a meta tag in <head />">
      <header className={classnames('hero hero--primary', styles.heroBanner)}>
        <div className="container">
          <h1 className={classnames(
            styles.hero__title,
          )}>
            <img src="img/favicon/logotype_main.png"></img>
          </h1>
          <h2><small className={styles.hero__subtitle}>{siteConfig.tagline}</small></h2>
          <div className={styles.buttons}>
            <Link
              className={classnames(
                'button button--outline button--primary',
                styles.button,
              )}
              to={'https://github.com/pypeclub/pype'}>
              Source Code
            </Link>
            <Link
              className={classnames(
                'button button--outline button--primary',
                styles.button,
              )}
              to={'mailto:info@pype.club'}>
              Get in touch
            </Link>
            <Link
              className={classnames(
                'button button--outline button--primary',
                styles.button,
              )}
              to={'https://discord.gg/sFNPWXG'}>
              Join our chat
            </Link>
            <Link
              className={classnames(
                'button button--outline button--primary',
                styles.button,
              )}
              to={'https://support.pype.club'}>
              Client Support
            </Link>

            <p>
            Helping VFX and animation studios that lack the resources to design and maintain a major software project in-house.</p>
            <p>
            We are your pipeline department, in a remote office.</p>

          </div>


        </div>
      </header>
      <main>

        {services && services.length && (
          <section className={classnames(styles.features,
                                        styles.center)}>
            <div className="container">
            <h2>Services</h2>
              <div className="row">
                {services.map((props, idx) => (
                  <Service key={idx} {...props} />
                ))}
              </div>
            </div>
          </section>
        )}
        <section className={classnames(styles.features,
                                        "darkBackground")}>
          <div className="container">
            <div className={classnames('row')}>
              <div className="col col--6">
              <img src="/img/frontpage/undraw_mind_map_cwng.svg" />
              </div>
              <div className="col col--6">
                <h2>What is Pype?
                </h2>
                    <p>Multi-platform open-source pipeline built around the <a href="https://getavalon.github.io/2.0/">Avalon </a> platform, expanding it with extra features and integrations. Pype connects asset database, project management and time tracking into a single modular system. It has tight integration with Ftrack, but it can also run independently.</p>

                    <p>
                    Avalon with Pype provides a safe and stable technical backbone for your studio, without the worry of a vendor lock. You will always have full access to the source and your project database will run locally.
                    </p>
              </div>
            </div>
          </div>
        </section>
        <section className={classnames(styles.features)}>
          <div className="container">
            <div className={classnames('row',)}>
                <div className="col col--6">
                <h2>About us
                </h2>
                <p>
                Our core team is formed from industry experts with years of production and pipeline experience. We perfectly understand the problems your studio is facing, because we’ve dealt with them, first hand, before. Instead of selling software, we offer our experience and time.
                </p>
                <p>Pype Club is a <a href="https://www.ftrack.com/en/developer/ftrack-developer-network">Ftrack Approved Developer</a>
                </p>
                </div>
                <div className="col col--6">
                <img src="/img/frontpage/undraw_programming.svg" />
                </div>
            </div>
          </div>
        </section>
        <section className={classnames(styles.gallery, "center darkBackground")}>
          <div className="container">
              <h2>Pype Integrations</h2>
              <div className={classnames('showcase',)}>
                <a className="link" href={useBaseUrl("features#maya")}>
                  <img src="/img/app_maya.png" alt="" title=""></img>
                  <span className="caption">Maya</span>
                </a>

                <a className="link" href={useBaseUrl("features#nuke")}>
                  <img src="/img/app_nuke.png" alt="" title=""></img>
                  <span className="caption">Nuke</span>
                </a>

                <a className="link" href={useBaseUrl("features#hiero")}>
                  <img src="/img/app_nuke.png" alt="" title=""></img>
                  <span className="caption">Nuke Studio</span>
                </a>

                <a className="link" href={useBaseUrl("features#hiero")}>
                  <img src="/img/app_hiero.png" alt="" title=""></img>
                  <span className="caption">Hiero</span>
                </a>

                <a className="link" href={useBaseUrl("features#houdini")}>
                  <img src="/img/app_houdini.png" alt="" title=""></img>
                  <span className="caption">Houdini</span>
                </a>

                <a className="link" href={useBaseUrl("features#blender")}>
                  <img src="/img/app_blender.png" alt="" title=""></img>
                  <span className="caption">Blender</span>
                </a>

                <a className="link" href={useBaseUrl("features#fusion")}>
                  <img src="/img/app_fusion.png" alt="" title=""></img>
                  <span className="caption">Fusion</span>
                </a>

                <a className="link" href={useBaseUrl("features#harmony")}>
                  <img src="/img/app_toonboom.png" alt="" title=""></img>
                  <span className="caption">Harmony</span>
                </a>

                <a className="link" href={useBaseUrl("features#photoshop")}>
                  <img src="/img/app_photoshop.png" alt="" title=""></img>
                  <span className="caption">Photoshop</span>
                </a>

                <a className="link" href={useBaseUrl("features#ftrack")}>
                  <img src="/img/app_ftrack.png" alt="" title=""></img>
                  <span className="caption">Ftrack</span>
                </a>

                <a className="link" href={useBaseUrl("features#clockify")}>
                  <img src="/img/app_clockify.png" alt="" title=""></img>
                  <span className="caption">Clockify</span>
                </a>

                <a className="link" href="">
                  <img src="/img/app_deadline.png" alt="" title=""></img>
                  <span className="caption">Deadline</span>
                </a>

                <a className="link" href="">
                  <img src="/img/app_muster.png" alt="" title=""></img>
                  <span className="caption">Muster</span>
                </a>

                <a className="link" href="">
                  <img src="/img/app_unreal.png" alt="" title=""></img>
                  <span className="caption">Unreal Engine</span>
                </a>

                <a className="link" href="">
                  <img src="/img/app_aftereffects.png" alt="" title=""></img>
                  <span className="caption">After Effects (Beta)</span>
                </a>

                <a className="link" href="">
                  <img src="/img/app_tvpaint.png" alt="" title=""></img>
                  <span className="caption">TV Paint (Beta)</span>
                </a>

              </div>

              <p> <span>In development by us or a community of <a href="https://github.com/getavalon/core/pulls">avalon core</a> developers.</span></p>

              <div className={classnames('showcase',)}>

                <a className="link" href="">
                  <img src="/img/app_storyboardpro.svg" alt="" title=""></img>
                  <span className="caption">Storyboard Pro</span>
                </a>
                <a className="link" href="">
                  <img src="/img/app_resolve.png" alt="" title=""></img>
                  <span className="caption">DaVinci Resolve</span>
                </a>

              </div>
          </div>
        </section>

        {collab && collab.length && (
          <section className={styles.collaborators}>
            <div className="">
              <h2>Collaborators</h2>
              <p><span>Studios and projects which are continuously helping pype grow and get better.</span></p>
              <div className="showcase">
                {collab.map((props, idx) => (
                  <Collaborator key={idx} {...props} />
                ))}
              </div>
            </div>
          </section>
        )}


        {clients && clients.length && (
          <section className={styles.gallery}>
            <div className="container">
              <h2>Clients</h2>
              <div className="showcase">
                {clients.map((props, idx) => (
                  <Client key={idx} {...props} />
                ))}
              </div>
            </div>
          </section>
        )}



      <div className="container">
        <BadgesSection/>
      </div>


      </main>
    </Layout>
  );
}

export default Home;
