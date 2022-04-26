module.exports = {
  title: 'openPYPE',
  tagline: 'Pipeline with support, for studios and remote teams.',
  url: 'http://openpype.io/',
  baseUrl: '/',
  organizationName: 'Orbi Tools s.r.o',
  projectName: 'openPype',
  favicon: 'img/favicon/favicon.ico',
  onBrokenLinks: 'ignore',
  customFields: {
  },
  presets: [
    [
      '@docusaurus/preset-classic', {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css')
        },
        gtag: {
        trackingID: 'G-DTKXMFENFY',
        // Optional fields.
        anonymizeIP: false, // Should IPs be anonymized?
      }
      }
    ],
    
  ],
  themeConfig: {
    colorMode: {
      // "light" | "dark"
      defaultMode: 'light',

      // Hides the switch in the navbar
      // Useful if you want to support a single color mode
      disableSwitch: true
    },
    announcementBar: {
      id: 'help_with_docs', // Any value that will identify this message.
      content:
      'Help us make this documentation better. <b><a href="https://github.com/pypeclub/OpenPype/tree/develop/website">Edit on github.</a></b>.',
      backgroundColor: '#fff', // Defaults to `#fff`.
      textColor: '#000', // Defaults to `#000`.
    },
    navbar: {
      style: 'dark',
      title: 'openPYPE',
      logo: {
        src: 'img/logos/splash_main.svg'
      },
      items: [
        {
          to: '/features',
          label: 'Features',
          position: 'left'
        }, {
          to: 'docs/artist_getting_started',
          label: 'User Docs',
          position: 'left'
        },
        {
          to: 'docs/system_introduction',
          label: 'Admin Docs',
          position: 'left'
        },
        {
          to: 'docs/dev_introduction',
          label: 'Dev Docs',
          position: 'left'
        },
          {
            to: 'https://pype.club',
            'aria-label': 'pypeclub',
            className: 'header-pypeclub-link',
            position: 'right',
          },{
          to: 'https://github.com/pypeclub',
          'aria-label': 'Github',
          className: 'header-github-link',
          position: 'right',
        }
      ]
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Pages',
          items: [
            {
              label: 'Features',
              to: 'features',
            },
            {
              label: 'Artist',
              to: 'docs/artist_getting_started',
            },
            {
              label: 'Admin',
              to: 'docs/admin_getting_started',
            }
          ]
        },
        {
          title: 'Community',
          items: [
            {
              label: 'Avalon Chat',
              to: 'https://gitter.im/getavalon/Lobby',
            },
            {
              label: 'OpenPype Chat',
              to: 'https://discord.gg/sFNPWXG',
            },
            {
              label: 'Github Discussions',
              to: 'https://github.com/pypeclub/pype/discussions',
            }
          ],
        },
      ],
      copyright: 'Copyright © 2021 Orbi Tools',
    },
    algolia: {
      apiKey: '5e01ee3bfbb744ca6f25d4b281ce38a9',
      indexName: 'openpype',
      // Optional: see doc section below
      contextualSearch: true,
      // Optional: Algolia search parameters
      searchParameters: {},
    }
  },
  stylesheets: [
        'https://use.fontawesome.com/releases/v5.7.2/css/all.css'
    ],
};
